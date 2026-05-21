from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re

from backend.logger import logger


@dataclass
class ConfidenceResult:
    score: float
    label: str
    factors: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_score": round(self.score, 4),
            "confidence_label": self.label,
            "confidence_factors": self.factors,
        }


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _label_from_score(score: float) -> str:
    if score >= 0.75:
        return "HIGH"
    if score >= 0.45:
        return "MEDIUM"
    return "LOW"


class AuditConfidenceScorer:
    """Computes confidence scores for AUDIT mode responses."""

    WEIGHTS = {
        "structured_parse_success": 0.30,
        "issue_completeness": 0.20,
        "duplicate_suppression": 0.10,
        "refusal_absent": 0.15,
        "response_length": 0.10,
        "no_fallback_parser": 0.15,
    }

    REFUSAL_PATTERNS = [
        re.compile(r"(?i)\b(?:I cannot|I can't|I am unable|I'm unable|I do not have access)"),
        re.compile(r"(?i)\b(?:not enough information|insufficient information|cannot analyze)"),
        re.compile(r"(?i)\b(?:refus|declin|unable to process)"),
    ]

    QUALITY_CAP_MAX_SCORE = 0.30
    FALLBACK_DEGRADED_CAP_MAX_SCORE = 0.25

    def compute(
        self,
        response_text: str,
        issue_count: int,
        structured_parse_failed: bool,
        fallback_used: bool = False,
        duplicate_suppressed: int = 0,
        input_quality_degraded: bool = False,
    ) -> ConfidenceResult:
        logger.info("[FallbackTrace] stage=audit_confidence_scorer_compute fallback_used=%s input_quality_degraded=%s", fallback_used, input_quality_degraded)
        factors: Dict[str, float] = {}

        parse_score = 0.0 if structured_parse_failed else 1.0
        factors["structured_parse_success"] = parse_score

        completeness_score = self._compute_completeness(issue_count, response_text)
        factors["issue_completeness"] = completeness_score

        duplicate_score = max(0.0, 1.0 - (duplicate_suppressed * 0.25))
        factors["duplicate_suppression"] = duplicate_score

        refusal_score = self._compute_refusal_score(response_text)
        factors["refusal_absent"] = refusal_score

        length_score = self._compute_length_score(response_text)
        factors["response_length"] = length_score

        fallback_score = 0.0 if fallback_used else 1.0
        factors["no_fallback_parser"] = fallback_score

        weighted = sum(
            factors[k] * self.WEIGHTS[k]
            for k in self.WEIGHTS
        )
        score = _clamp(weighted)

        if fallback_used and input_quality_degraded:
            score = min(score, self.FALLBACK_DEGRADED_CAP_MAX_SCORE)
            logger.warning(
                "[Confidence] AUDIT -> fallback+degraded cap applied: score=%.2f (max=%.2f)",
                score, self.FALLBACK_DEGRADED_CAP_MAX_SCORE,
            )
        elif input_quality_degraded:
            score = min(score, self.QUALITY_CAP_MAX_SCORE)
            logger.warning(
                "[Confidence] AUDIT -> quality-degraded cap applied: score=%.2f (max=%.2f)",
                score, self.QUALITY_CAP_MAX_SCORE,
            )

        label = _label_from_score(score)

        logger.info(
            "[Confidence] AUDIT -> score=%.2f label=%s parse_ok=%s issues=%d fallback=%s duplicates=%d quality_degraded=%s",
            score, label, not structured_parse_failed, issue_count, fallback_used, duplicate_suppressed, input_quality_degraded,
        )

        return ConfidenceResult(score=score, label=label, factors=factors)

    def _compute_completeness(self, issue_count: int, response_text: str) -> float:
        if issue_count == 0:
            return 0.3
        has_titles = bool(re.search(r"(?im)^Issue:", response_text)) or bool(re.search(r"issue_title", response_text))
        has_severities = bool(re.search(r"(?im)^Severity:", response_text)) or bool(re.search(r"severity", response_text))
        has_quotes = bool(re.search(r"(?im)^Quoted Text:", response_text)) or bool(re.search(r"quoted_text", response_text))
        present = sum([has_titles, has_severities, has_quotes])
        return _clamp(0.4 + (present / 3) * 0.6)

    def _compute_refusal_score(self, response_text: str) -> float:
        for pattern in self.REFUSAL_PATTERNS:
            if pattern.search(response_text):
                return 0.0
        return 1.0

    def _compute_length_score(self, response_text: str) -> float:
        word_count = len(response_text.split())
        if word_count >= 100:
            return 1.0
        if word_count >= 50:
            return 0.8
        if word_count >= 20:
            return 0.5
        return 0.2


class AdvisoryConfidenceScorer:
    """Computes confidence scores for ADVISORY mode responses."""

    WEIGHTS = {
        "refusal_absent": 0.25,
        "legal_topic_relevance": 0.20,
        "answer_completeness": 0.20,
        "no_generic_penalty": 0.20,
        "no_hallucination_warning": 0.15,
    }

    REFUSAL_PATTERNS = [
        re.compile(r"(?i)\b(?:I cannot|I can't|I am unable|I'm unable)"),
        re.compile(r"(?i)\b(?:I am not a lawyer|I am not an attorney|not legal advice)"),
        re.compile(r"(?i)\b(?:consult a lawyer|consult an attorney|seek legal counsel)"),
    ]

    LEGAL_TOPIC_KEYWORDS = [
        "contract", "clause", "liability", "indemnif", "termination",
        "confidential", "breach", "damages", "jurisdiction", "governing law",
        "arbitration", "compliance", "regulation", "statute", "obligation",
        "warranty", "disclaimer", "intellectual property", "copyright",
        "trademark", "patent", "non-disclosure", "NDA", "employment",
        "severance", "non-compete", "non-solicit",
    ]

    GENERIC_PHRASES = [
        re.compile(r"(?i)\b(?:it depends|this is a complex|there are many factors)"),
        re.compile(r"(?i)\b(?:generally speaking|in general|typically)"),
        re.compile(r"(?i)\b(?:I would recommend|you should consider)"),
    ]

    HALLUCINATION_PATTERNS = [
        re.compile(r"(?i)\b(?:I believe|I think|it seems like|probably)"),
        re.compile(r"(?i)\b(?:may or may not|could potentially|might be)"),
        re.compile(r"(?i)\b(?:to the best of my knowledge|as far as I know)"),
    ]

    QUALITY_CAP_MAX_SCORE = 0.30
    FALLBACK_DEGRADED_CAP_MAX_SCORE = 0.25

    def compute(self, response_text: str, user_query: str = "", input_quality_degraded: bool = False, fallback_used: bool = False) -> ConfidenceResult:
        logger.info("[FallbackTrace] stage=advisory_confidence_scorer_compute fallback_used=%s input_quality_degraded=%s", fallback_used, input_quality_degraded)
        factors: Dict[str, float] = {}

        refusal_score = self._compute_refusal_score(response_text)
        factors["refusal_absent"] = refusal_score

        legal_score = self._compute_legal_relevance(response_text, user_query)
        factors["legal_topic_relevance"] = legal_score

        completeness_score = self._compute_completeness(response_text)
        factors["answer_completeness"] = completeness_score

        generic_score = self._compute_generic_score(response_text)
        factors["no_generic_penalty"] = generic_score

        hallucination_score = self._compute_hallucination_score(response_text)
        factors["no_hallucination_warning"] = hallucination_score

        weighted = sum(
            factors[k] * self.WEIGHTS[k]
            for k in self.WEIGHTS
        )
        score = _clamp(weighted)

        if fallback_used and input_quality_degraded:
            score = min(score, self.FALLBACK_DEGRADED_CAP_MAX_SCORE)
            logger.warning(
                "[Confidence] ADVISORY -> fallback+degraded cap applied: score=%.2f (max=%.2f)",
                score, self.FALLBACK_DEGRADED_CAP_MAX_SCORE,
            )
        elif input_quality_degraded:
            score = min(score, self.QUALITY_CAP_MAX_SCORE)
            logger.warning(
                "[Confidence] ADVISORY -> quality-degraded cap applied: score=%.2f (max=%.2f)",
                score, self.QUALITY_CAP_MAX_SCORE,
            )

        label = _label_from_score(score)

        logger.info(
            "[Confidence] ADVISORY -> score=%.2f label=%s legal=%.2f generic=%.2f hallucination=%.2f quality_degraded=%s fallback=%s",
            score, label, legal_score, generic_score, hallucination_score, input_quality_degraded, fallback_used,
        )

        return ConfidenceResult(score=score, label=label, factors=factors)

    def _compute_refusal_score(self, response_text: str) -> float:
        for pattern in self.REFUSAL_PATTERNS:
            if pattern.search(response_text):
                return 0.0
        return 1.0

    def _compute_legal_relevance(self, response_text: str, user_query: str) -> float:
        combined = f"{response_text} {user_query}".lower()
        matches = sum(1 for kw in self.LEGAL_TOPIC_KEYWORDS if kw in combined)
        return _clamp(min(1.0, matches / 4.0))

    def _compute_completeness(self, response_text: str) -> float:
        word_count = len(response_text.split())
        if word_count >= 200:
            return 1.0
        if word_count >= 100:
            return 0.8
        if word_count >= 50:
            return 0.6
        if word_count >= 20:
            return 0.4
        return 0.2

    def _compute_generic_score(self, response_text: str) -> float:
        matches = sum(1 for pattern in self.GENERIC_PHRASES if pattern.search(response_text))
        return _clamp(1.0 - (matches * 0.3))

    def _compute_hallucination_score(self, response_text: str) -> float:
        matches = sum(1 for pattern in self.HALLUCINATION_PATTERNS if pattern.search(response_text))
        return _clamp(1.0 - (matches * 0.25))


audit_scorer = AuditConfidenceScorer()
advisory_scorer = AdvisoryConfidenceScorer()
