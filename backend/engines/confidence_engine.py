from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re

from backend.logger import logger


@dataclass
class ConfidenceResult:
    score: float
    label: str
    factors: Dict[str, float] = field(default_factory=dict)
    penalties: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_score": round(self.score, 4),
            "confidence_label": self.label,
            "confidence_factors": self.factors,
            "confidence_penalties": self.penalties,
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
    """Computes confidence scores for AUDIT mode responses.

    Uses accuracy-proximate signals instead of process signals.
    Weights reflect expected correlation with correctness:
    - qt_match_rate (0.30): strongest signal — verifies quotes against document
    - category_validity (0.12): necessary condition for correctness
    - explanation_quality (0.12): analysis depth proxy
    - improvement_quality (0.10): understanding proxy
    - severity_consistency (0.08): calibration proxy
    - location_diversity (0.08): thoroughness proxy
    - count_signal (0.08): issue count calibration
    - domain_signal (0.07): context quality
    - parse_success (0.05): baseline (low discriminative power)
    """

    WEIGHTS = {
        "qt_match_rate": 0.30,
        "category_validity": 0.12,
        "explanation_quality": 0.12,
        "improvement_quality": 0.10,
        "severity_consistency": 0.08,
        "location_diversity": 0.08,
        "count_signal": 0.08,
        "domain_signal": 0.07,
        "parse_success": 0.05,
    }

    VALID_CATEGORIES = {
        "structural inconsistency", "indemnification", "liability exposure",
        "governing law", "residuals", "enforceability weakness",
        "negotiation imbalance", "privacy risk", "confidentiality termination",
        "intellectual property", "restrictive covenants",
    }

    REFUSAL_PATTERNS = [
        re.compile(r"(?i)\b(?:I cannot|I can't|I am unable|I'm unable|I do not have access)"),
        re.compile(r"(?i)\b(?:not enough information|insufficient information|cannot analyze)"),
        re.compile(r"(?i)\b(?:refus|declin|unable to process)"),
    ]

    POLICY_PENALTY = 0.50
    NON_LEGAL_PENALTY = 0.25
    DUPLICATE_PENALTY = 0.75

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
        issues: Optional[List] = None,
        doc_text: str = "",
        policy_detected: bool = False,
        non_legal_detected: bool = False,
        domain_confidence: float = 0.0,
    ) -> ConfidenceResult:
        logger.info("[FallbackTrace] stage=audit_confidence_scorer_compute fallback_used=%s input_quality_degraded=%s", fallback_used, input_quality_degraded)
        factors: Dict[str, float] = {}

        parse_score = 0.0 if structured_parse_failed else 1.0
        factors["parse_success"] = parse_score
        logger.info("[Confidence] factor=parse_success value=%.4f weight=%.2f contribution=%.4f", parse_score, self.WEIGHTS["parse_success"], parse_score * self.WEIGHTS["parse_success"])

        qt_match_rate = self._compute_qt_match_rate(issues, doc_text)
        factors["qt_match_rate"] = qt_match_rate
        logger.info("[Confidence] factor=qt_match_rate value=%.4f weight=%.2f contribution=%.4f", qt_match_rate, self.WEIGHTS["qt_match_rate"], qt_match_rate * self.WEIGHTS["qt_match_rate"])

        category_validity = self._compute_category_validity(issues)
        factors["category_validity"] = category_validity
        logger.info("[Confidence] factor=category_validity value=%.4f weight=%.2f contribution=%.4f", category_validity, self.WEIGHTS["category_validity"], category_validity * self.WEIGHTS["category_validity"])

        explanation_quality = self._compute_explanation_quality(issues)
        factors["explanation_quality"] = explanation_quality
        logger.info("[Confidence] factor=explanation_quality value=%.4f weight=%.2f contribution=%.4f", explanation_quality, self.WEIGHTS["explanation_quality"], explanation_quality * self.WEIGHTS["explanation_quality"])

        improvement_quality = self._compute_improvement_quality(issues)
        factors["improvement_quality"] = improvement_quality
        logger.info("[Confidence] factor=improvement_quality value=%.4f weight=%.2f contribution=%.4f", improvement_quality, self.WEIGHTS["improvement_quality"], improvement_quality * self.WEIGHTS["improvement_quality"])

        severity_consistency = self._compute_severity_consistency(issues)
        factors["severity_consistency"] = severity_consistency
        logger.info("[Confidence] factor=severity_consistency value=%.4f weight=%.2f contribution=%.4f", severity_consistency, self.WEIGHTS["severity_consistency"], severity_consistency * self.WEIGHTS["severity_consistency"])

        location_diversity = self._compute_location_diversity(issues)
        factors["location_diversity"] = location_diversity
        logger.info("[Confidence] factor=location_diversity value=%.4f weight=%.2f contribution=%.4f", location_diversity, self.WEIGHTS["location_diversity"], location_diversity * self.WEIGHTS["location_diversity"])

        count_signal = self._compute_count_signal(issue_count, doc_text)
        factors["count_signal"] = count_signal
        logger.info("[Confidence] factor=count_signal value=%.4f weight=%.2f contribution=%.4f", count_signal, self.WEIGHTS["count_signal"], count_signal * self.WEIGHTS["count_signal"])

        domain_signal = _clamp(domain_confidence)
        factors["domain_signal"] = domain_signal
        logger.info("[Confidence] factor=domain_signal value=%.4f weight=%.2f contribution=%.4f", domain_signal, self.WEIGHTS["domain_signal"], domain_signal * self.WEIGHTS["domain_signal"])

        base_score = sum(
            factors[k] * self.WEIGHTS[k]
            for k in self.WEIGHTS
        )
        logger.info("[Confidence] base_score=%.4f (before penalties)", base_score)

        penalties: Dict[str, float] = {}
        penalty_multiplier = 1.0

        if policy_detected:
            penalties["policy_detected"] = self.POLICY_PENALTY
            penalty_multiplier *= self.POLICY_PENALTY
            logger.warning("[Confidence] penalty=policy_detected multiplier=%.2f", self.POLICY_PENALTY)

        if non_legal_detected:
            penalties["non_legal_detected"] = self.NON_LEGAL_PENALTY
            penalty_multiplier *= self.NON_LEGAL_PENALTY
            logger.warning("[Confidence] penalty=non_legal_detected multiplier=%.2f", self.NON_LEGAL_PENALTY)

        if duplicate_suppressed > 0:
            penalties["duplicate_suppression_penalty"] = self.DUPLICATE_PENALTY
            penalty_multiplier *= self.DUPLICATE_PENALTY
            logger.warning("[Confidence] penalty=duplicate_suppression multiplier=%.2f suppressed=%d", self.DUPLICATE_PENALTY, duplicate_suppressed)

        score = _clamp(base_score) * penalty_multiplier
        logger.info("[Confidence] after_penalties score=%.4f penalty_multiplier=%.4f", score, penalty_multiplier)

        if structured_parse_failed:
            score = min(score, 0.25)
            logger.warning("[Confidence] AUDIT -> parse-failed cap applied: score=%.2f (max=0.25)", score)

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
            "[Confidence] AUDIT -> score=%.2f label=%s parse_ok=%s issues=%d fallback=%s duplicates=%d quality_degraded=%s policy=%s non_legal=%s",
            score, label, not structured_parse_failed, issue_count, fallback_used, duplicate_suppressed, input_quality_degraded, policy_detected, non_legal_detected,
        )

        return ConfidenceResult(score=score, label=label, factors=factors, penalties=penalties)

    def _compute_qt_match_rate(self, issues: Optional[List], doc_text: str) -> float:
        if not issues:
            return 0.5
        if not doc_text:
            return 0.5
        text_lower = doc_text.lower()
        matches = 0
        for issue in issues:
            qt = getattr(issue, 'quoted_text', None) or ''
            qt = qt.lower().strip()
            if len(qt) < 20:
                matches += 1
            elif qt in text_lower:
                matches += 1
            else:
                truncated = qt[:40]
                if truncated in text_lower:
                    matches += 0.5
        return matches / len(issues)

    def _compute_category_validity(self, issues: Optional[List]) -> float:
        if not issues:
            return 0.5
        valid_count = 0
        for issue in issues:
            category = getattr(issue, 'category', None) or ''
            if category.lower() in self.VALID_CATEGORIES:
                valid_count += 1
        return valid_count / len(issues)

    def _compute_explanation_quality(self, issues: Optional[List]) -> float:
        if not issues:
            return 0.3
        total_words = 0
        for issue in issues:
            explanation = getattr(issue, 'risk_explanation', None) or ''
            total_words += len(explanation.split())
        avg_words = total_words / len(issues)
        if avg_words >= 30:
            return 1.0
        if avg_words >= 20:
            return 0.8
        if avg_words >= 10:
            return 0.6
        if avg_words >= 5:
            return 0.4
        return 0.2

    def _compute_improvement_quality(self, issues: Optional[List]) -> float:
        if not issues:
            return 0.3
        total_words = 0
        for issue in issues:
            improvement = getattr(issue, 'suggested_improvement', None) or ''
            total_words += len(improvement.split())
        avg_words = total_words / len(issues)
        if avg_words >= 25:
            return 1.0
        if avg_words >= 15:
            return 0.8
        if avg_words >= 8:
            return 0.6
        if avg_words >= 3:
            return 0.4
        return 0.2

    def _compute_severity_consistency(self, issues: Optional[List]) -> float:
        if not issues:
            return 0.5
        severities = []
        for issue in issues:
            sev = getattr(issue, 'severity', None) or 'MEDIUM'
            sev = sev.upper()
            if sev == 'CRITICAL':
                severities.append(4)
            elif sev == 'HIGH':
                severities.append(3)
            elif sev == 'MEDIUM':
                severities.append(2)
            else:
                severities.append(1)
        if not severities:
            return 0.5
        avg = sum(severities) / len(severities)
        has_mix = len(set(severities)) > 1
        if has_mix:
            return 1.0
        if 1.5 <= avg <= 3.5:
            return 0.8
        return 0.5

    def _compute_location_diversity(self, issues: Optional[List]) -> float:
        if not issues:
            return 0.5
        locations = set()
        for issue in issues:
            loc = getattr(issue, 'location', None) or 'unknown'
            locations.add(loc.lower())
        unique_count = len(locations)
        if unique_count >= 3:
            return 1.0
        if unique_count == 2:
            return 0.7
        return 0.4

    def _compute_count_signal(self, issue_count: int, doc_text: str) -> float:
        if not doc_text:
            return 0.5
        word_count = len(doc_text.split())
        if word_count < 200:
            expected = 1
        elif word_count < 500:
            expected = 2
        elif word_count < 1000:
            expected = 3
        else:
            expected = 4
        ratio = issue_count / expected if expected > 0 else 0
        if 0.5 <= ratio <= 2.0:
            return 1.0
        if 0.25 <= ratio <= 3.0:
            return 0.7
        return 0.4


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
