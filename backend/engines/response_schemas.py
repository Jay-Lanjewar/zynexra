from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from enum import Enum
import re
import time

from backend.logger import logger

SCHEMA_VERSION = 1


class ResponseMode(str, Enum):
    AUDIT = "AUDIT"
    REDACTION = "REDACTION"
    ADVISORY = "ADVISORY"


@dataclass
class AuditIssue:
    issue_title: str = ""
    severity: str = ""
    category: str = ""
    location: str = ""
    quoted_text: str = ""
    risk_explanation: str = ""
    suggested_improvement: str = ""
    contradiction_detected: Optional[bool] = None
    original_category: Optional[str] = None
    related_clause_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "issue_title": self.issue_title,
            "severity": self.severity,
            "category": self.category,
            "location": self.location,
            "quoted_text": self.quoted_text,
            "risk_explanation": self.risk_explanation,
            "suggested_improvement": self.suggested_improvement,
        }
        if self.contradiction_detected is not None:
            res["contradiction_detected"] = self.contradiction_detected
        if self.original_category is not None:
            res["original_category"] = self.original_category
        if self.related_clause_count is not None:
            res["related_clause_count"] = self.related_clause_count
        return res



@dataclass
class AuditResponse:
    success: bool = True
    model: str = ""
    mode: str = "AUDIT"
    response_type: str = "audit"
    schema_version: int = SCHEMA_VERSION
    issue_count: int = 0
    issues: List[Dict[str, str]] = field(default_factory=list)
    structured_parse_failed: bool = False
    legacy_text: str = ""
    confidence_score: float = 0.0
    confidence_label: str = ""
    fallback_used: bool = False
    quality_warning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class RedactionEntity:
    entity_type: str = ""
    original_text: str = ""
    replacement: str = ""
    confidence: float = 0.0
    start: int = 0
    end: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RedactionResponse:
    success: bool = True
    model: str = ""
    mode: str = "REDACTION"
    response_type: str = "redaction"
    schema_version: int = SCHEMA_VERSION
    issue_count: int = 0
    issues: List[Any] = field(default_factory=list)
    structured_parse_failed: bool = False
    legacy_text: str = ""
    redacted_text: str = ""
    original_text: str = ""
    redaction_entities: List[Dict[str, Any]] = field(default_factory=list)
    redaction_count: int = 0
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AdvisoryResponse:
    success: bool = True
    model: str = ""
    mode: str = "ADVISORY"
    response_type: str = "advisory"
    schema_version: int = SCHEMA_VERSION
    issue_count: int = 0
    issues: List[Any] = field(default_factory=list)
    structured_parse_failed: bool = False
    legacy_text: str = ""
    advisory_text: str = ""
    confidence_score: float = 0.0
    confidence_label: str = ""
    quality_warning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.metadata:
            result["metadata"] = self.metadata
        return result


def validate_audit_response(response: Dict[str, Any]) -> bool:
    required_fields = [
        "success", "model", "mode", "response_type", "schema_version",
        "issue_count", "issues", "structured_parse_failed", "legacy_text"
    ]
    for field_name in required_fields:
        if field_name not in response:
            logger.warning(f"[Schema] Audit response missing field: {field_name}")
            return False

    if response.get("schema_version") != SCHEMA_VERSION:
        logger.warning(
            f"[Schema] Audit response schema_version mismatch: "
            f"expected {SCHEMA_VERSION}, got {response.get('schema_version')}"
        )
        return False

    if not isinstance(response.get("issues"), list):
        logger.warning("[Schema] Audit response 'issues' must be a list")
        return False

    confidence_score = response.get("confidence_score")
    if confidence_score is not None:
        if not isinstance(confidence_score, (int, float)) or not (0.0 <= confidence_score <= 1.0):
            logger.warning(f"[Schema] Audit response confidence_score out of range: {confidence_score}")

    logger.info("[Schema] Audit response validated")
    return True


def validate_redaction_response(response: Dict[str, Any]) -> bool:
    required_fields = [
        "success", "model", "mode", "response_type", "schema_version",
        "redacted_text", "redaction_entities", "redaction_count"
    ]
    for field_name in required_fields:
        if field_name not in response:
            logger.warning(f"[Schema] Redaction response missing field: {field_name}")
            return False

    if response.get("schema_version") != SCHEMA_VERSION:
        logger.warning(
            f"[Schema] Redaction response schema_version mismatch: "
            f"expected {SCHEMA_VERSION}, got {response.get('schema_version')}"
        )
        return False

    if not isinstance(response.get("redaction_entities"), list):
        logger.warning("[Schema] Redaction response 'redaction_entities' must be a list")
        return False

    logger.info("[Schema] Redaction response validated")
    return True


def validate_advisory_response(response: Dict[str, Any]) -> bool:
    required_fields = [
        "success", "model", "mode", "response_type", "schema_version",
        "advisory_text"
    ]
    for field_name in required_fields:
        if field_name not in response:
            logger.warning(f"[Schema] Advisory response missing field: {field_name}")
            return False

    if response.get("schema_version") != SCHEMA_VERSION:
        logger.warning(
            f"[Schema] Advisory response schema_version mismatch: "
            f"expected {SCHEMA_VERSION}, got {response.get('schema_version')}"
        )
        return False

    confidence_score = response.get("confidence_score")
    if confidence_score is not None:
        if not isinstance(confidence_score, (int, float)) or not (0.0 <= confidence_score <= 1.0):
            logger.warning(f"[Schema] Advisory response confidence_score out of range: {confidence_score}")

    logger.info("[Schema] Advisory response validated")
    return True


def validate_response(response: Dict[str, Any], mode: str) -> bool:
    mode_upper = mode.upper()
    if mode_upper == "AUDIT":
        return validate_audit_response(response)
    elif mode_upper == "REDACTION":
        return validate_redaction_response(response)
    elif mode_upper == "ADVISORY":
        return validate_advisory_response(response)
    else:
        logger.warning(f"[Schema] Unknown mode for validation: {mode}")
        return False


def build_audit_response(
    complete_response: str,
    model: str,
    issues: Optional[List[Dict[str, str]]] = None,
    structured_parse_failed: bool = False,
    confidence_score: float = 0.0,
    confidence_label: str = "",
    fallback_used: bool = False,
    quality_warning: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    issue_list = issues or []

    response = AuditResponse(
        success=True,
        model=model,
        mode="AUDIT",
        response_type="audit",
        schema_version=SCHEMA_VERSION,
        issue_count=len(issue_list),
        issues=issue_list,
        structured_parse_failed=structured_parse_failed,
        legacy_text=complete_response,
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        fallback_used=fallback_used,
        quality_warning=quality_warning,
        metadata=metadata or {},
    )

    response_dict = response.to_dict()

    sv_start = time.time()
    schema_valid = validate_audit_response(response_dict)
    sv_ms = (time.time() - sv_start) * 1000
    logger.info("[Perf] schema_validation_ms=%.0f", sv_ms)

    if not schema_valid:
        logger.warning("[Schema] Built audit response failed validation, returning legacy format")
        return {
            "success": True,
            "model": model,
            "mode": "AUDIT",
            "response_type": "audit",
            "schema_version": SCHEMA_VERSION,
            "issue_count": len(issue_list),
            "issues": issue_list,
            "structured_parse_failed": structured_parse_failed,
            "legacy_text": complete_response,
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "fallback_used": fallback_used,
            "quality_warning": quality_warning,
            "metadata": metadata or {},
        }

    return response_dict


def build_redaction_response(
    model: str,
    original_text: str,
    redacted_text: str,
    redaction_entities: Optional[List[Dict[str, Any]]] = None,
    fallback_used: bool = False
) -> Dict[str, Any]:
    entities_list = redaction_entities or []

    response = RedactionResponse(
        success=True,
        model=model,
        mode="REDACTION",
        response_type="redaction",
        schema_version=SCHEMA_VERSION,
        issue_count=0,
        issues=[],
        structured_parse_failed=False,
        legacy_text=redacted_text,
        redacted_text=redacted_text,
        original_text=original_text,
        redaction_entities=entities_list,
        redaction_count=len(entities_list),
        fallback_used=fallback_used,
    )

    response_dict = response.to_dict()

    if not validate_redaction_response(response_dict):
        logger.warning("[Schema] Built redaction response failed validation, returning legacy format")
        return {
            "success": True,
            "model": model,
            "mode": "REDACTION",
            "response_type": "redaction",
            "schema_version": SCHEMA_VERSION,
            "issue_count": 0,
            "issues": [],
            "structured_parse_failed": False,
            "legacy_text": redacted_text,
            "redacted_text": redacted_text,
            "original_text": original_text,
            "redaction_entities": entities_list,
            "redaction_count": len(entities_list),
            "fallback_used": fallback_used,
        }

    return response_dict


def build_advisory_response(
    complete_response: str,
    model: str,
    confidence_score: float = 0.0,
    confidence_label: str = "",
    quality_warning: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response = AdvisoryResponse(
        success=True,
        model=model,
        mode="ADVISORY",
        response_type="advisory",
        schema_version=SCHEMA_VERSION,
        issue_count=0,
        issues=[],
        structured_parse_failed=False,
        legacy_text=complete_response,
        advisory_text=complete_response,
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        quality_warning=quality_warning,
        metadata=metadata or {},
    )

    response_dict = response.to_dict()

    if not validate_advisory_response(response_dict):
        logger.warning("[Schema] Built advisory response failed validation, returning legacy format")
        return {
            "success": True,
            "model": model,
            "mode": "ADVISORY",
            "response_type": "advisory",
            "schema_version": SCHEMA_VERSION,
            "issue_count": 0,
            "issues": [],
            "structured_parse_failed": False,
            "legacy_text": complete_response,
            "advisory_text": complete_response,
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "quality_warning": quality_warning,
            "metadata": metadata or {},
        }

    return response_dict


def convert_history_record_to_response(record: Dict[str, Any], record_type: str, model: str) -> Dict[str, Any]:
    if record_type == "audit":
        return build_audit_response(
            complete_response=record.get("raw_response", ""),
            model=model,
            issues=record.get("issues", []),
            structured_parse_failed=not record.get("issues"),
            confidence_score=record.get("confidence_score", 0.0),
            confidence_label=record.get("confidence_label", ""),
            fallback_used=record.get("fallback_used", False),
            quality_warning=record.get("quality_warning", ""),
            metadata=record.get("metadata", {}),
        )
    elif record_type == "redaction":
        return build_redaction_response(
            model=model,
            original_text=record.get("redacted_text", ""),
            redacted_text=record.get("redacted_text", ""),
            redaction_entities=list(record.get("entities", {}).values()) if record.get("entities") else [],
            fallback_used=False
        )
    elif record_type == "advisory":
        return build_advisory_response(
            complete_response=record.get("messages", []),
            model=model,
            confidence_score=record.get("confidence_score", 0.0),
            confidence_label=record.get("confidence_label", ""),
            quality_warning=record.get("quality_warning", ""),
            metadata=record.get("metadata", {}),
        )
    else:
        logger.warning(f"[Schema] Unknown record_type for conversion: {record_type}")
        return {"success": False, "error": "Unknown record type"}


def get_legacy_text_for_export(record: Dict[str, Any], record_type: str) -> str:
    if record_type == "audit":
        return record.get("raw_response", "")
    elif record_type == "redaction":
        return record.get("redacted_text", "")
    elif record_type == "advisory":
        messages = record.get("messages", [])
        if isinstance(messages, list):
            return "\n".join(
                f"User: {m.get('user', '')}\nAssistant: {m.get('assistant', '')}"
                for m in messages if isinstance(m, dict)
            )
        return str(messages)
    return ""


@dataclass
class PolicyResponse:
    success: bool = True
    model: str = ""
    mode: str = "AUDIT"
    response_type: str = "policy"
    schema_version: int = SCHEMA_VERSION
    issue_count: int = 0
    issues: List[Any] = field(default_factory=list)
    structured_parse_failed: bool = False
    legacy_text: str = ""
    policy_type: str = ""
    policy_explanation: str = ""
    policy_confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_policy_response(
    model: str,
    policy_type: str,
    policy_explanation: str,
    policy_confidence: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response = PolicyResponse(
        success=True,
        model=model,
        mode="AUDIT",
        response_type="policy",
        schema_version=SCHEMA_VERSION,
        issue_count=0,
        issues=[],
        structured_parse_failed=False,
        legacy_text="",
        policy_type=policy_type,
        policy_explanation=policy_explanation,
        policy_confidence=policy_confidence,
        metadata=metadata or {},
    )

    logger.info("[PolicyDetection] Policy response built: type=%s confidence=%.4f", policy_type, policy_confidence)
    return response.to_dict()


@dataclass
class NonLegalResponse:
    success: bool = True
    model: str = ""
    mode: str = "AUDIT"
    response_type: str = "non_legal"
    schema_version: int = SCHEMA_VERSION
    issue_count: int = 0
    issues: List[Any] = field(default_factory=list)
    structured_parse_failed: bool = False
    legacy_text: str = ""
    content_type: str = ""
    content_explanation: str = ""
    domain_confidence: float = 0.0
    legal_keyword_ratio: float = 0.0
    structure_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


NON_LEGAL_CONTENT_TYPES: Dict[str, str] = {
    "Educational Material": "This document appears to be educational or instructional content such as textbook excerpts, lecture notes, study guides, or learning materials.",
    "Questions or Assignments": "This document appears to contain questions, problem sets, assignments, or examination content rather than a contractual agreement.",
    "General Text or Notes": "This document appears to be general text, notes, articles, or other non-contractual written content.",
    "Non-Contract Communication": "This document appears to be a non-contractual communication such as a memo, email, announcement, or informal message.",
    "Uncategorized Non-Legal": "This document does not appear to be a legal contract, agreement, or policy document. It likely contains general information or narrative text.",
}

NON_LEGAL_CONTENT_PATTERNS: Dict[str, list] = {
    "Educational Material": [
        r"(?i)\b(?:chapter|textbook|syllabus|curriculum|course\s+(?:outline|content|material|notes?|work)|lecture\s+(?:notes?|content|slides?)|study\s+(?:guide|material|notes?)|learning\s+(?:objective|outcome|resource)|lesson\s+(?:plan|content)|tutorial|worksheet|handout)\b",
        r"(?i)\b(?:define|explain|discuss|describe|compare|contrast|summarize|outline|identify|list|illustrate)\b.*\?",
        r"(?i)\b(?:equation|formula|theorem|proof|hypothesis|experiment|laboratory|lab\s+(?:report|manual|exercise))\b",
    ],
    "Questions or Assignments": [
        r"(?i)\b(?:question|answer|problem\s+(?:set|statement)|assignment|homework|exercise|task)\b",
        r"(?i)^\s*(?:\d+[\.\)]\s*|[A-Z][\.\)]\s*)(?:what|which|who|where|when|why|how|explain|describe|define|list|compare)\b",
        r"(?i)\b(?:multiple\s+choice|true\s*(?:/|or)\s*false|fill\s+in\s+the\s+blank|short\s+answer|essay\s+question)\b",
    ],
    "General Text or Notes": [
        r"(?i)\b(?:note|notes|summary|overview|introduction|background|context|purpose\s+of\s+(?:this|the))\b",
        r"(?i)\b(?:i\s+(?:think|believe|feel|argue|contend|propose|suggest|would\s+say))\b",
        r"(?i)\b(?:in\s+(?:this|my)\s+(?:paper|essay|article|post|report|analysis))\b",
    ],
    "Non-Contract Communication": [
        r"(?i)\b(?:dear|hello|hi|greetings)\s+(?:all|team|everyone|colleagues?|sir|madam)\b",
        r"(?i)\b(?:thanks|thank\s+you|regards|sincerely|best|cheers)\s*[,!]?\s*$",
        r"(?i)\b(?:meeting\s+(?:notes?|minutes?|agenda|summary|recap)|follow.up|action\s+items?)\b",
    ],
}

NON_LEGAL_SUPPRESSION_MESSAGE = (
    "This document does not appear to be a legal contract or agreement and has "
    "been flagged as non-contract content: {content_type}. Only contractual "
    "documents are processed through the legal-risk audit pipeline."
)


def classify_non_legal_content(text: str) -> tuple[str, str, float]:
    """Classify the type of non-legal content detected in the text."""
    if not text or not text.strip():
        return "Uncategorized Non-Legal", NON_LEGAL_CONTENT_TYPES["Uncategorized Non-Legal"], 0.0

    best_type = "Uncategorized Non-Legal"
    best_score = 0.0
    text_lower = text.lower()

    for content_type, patterns in NON_LEGAL_CONTENT_PATTERNS.items():
        score = 0.0
        for pattern in patterns:
            matches = len(re.findall(pattern, text_lower))
            score += matches
        avg = score / len(patterns) if patterns else 0.0
        if avg > best_score:
            best_score = avg
            best_type = content_type

    explanation = NON_LEGAL_CONTENT_TYPES.get(best_type, NON_LEGAL_CONTENT_TYPES["Uncategorized Non-Legal"])
    return best_type, explanation, best_score


def build_non_legal_response(
    model: str,
    content_type: str,
    content_explanation: str,
    domain_confidence: float = 0.0,
    legal_keyword_ratio: float = 0.0,
    structure_score: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response = NonLegalResponse(
        success=True,
        model=model,
        mode="AUDIT",
        response_type="non_legal",
        schema_version=SCHEMA_VERSION,
        issue_count=0,
        issues=[],
        structured_parse_failed=False,
        legacy_text="",
        content_type=content_type,
        content_explanation=content_explanation,
        domain_confidence=domain_confidence,
        legal_keyword_ratio=legal_keyword_ratio,
        structure_score=structure_score,
        metadata=metadata or {},
    )

    logger.info(
        "[NonLegalDetection] Non-legal response built: type=%s domain_confidence=%.4f",
        content_type, domain_confidence,
    )
    return response.to_dict()


def build_refusal_response(refusal_message: str, model: str, mode: str = "AUDIT") -> Dict[str, Any]:
    mode_upper = mode.upper()

    base_response = {
        "success": False,
        "model": model,
        "mode": mode_upper,
        "response_type": mode_upper.lower(),
        "schema_version": SCHEMA_VERSION,
        "issue_count": 0,
        "issues": [],
        "structured_parse_failed": True,
        "legacy_text": refusal_message,
        "confidence_score": 0.0,
        "confidence_label": "LOW",
        "fallback_used": False,
        "quality_warning": "",
        "metadata": {},
    }

    if mode_upper == "REDACTION":
        base_response["redacted_text"] = ""
        base_response["original_text"] = ""
        base_response["redaction_entities"] = []
        base_response["redaction_count"] = 0
    elif mode_upper == "ADVISORY":
        base_response["advisory_text"] = refusal_message

    logger.info(f"[Schema] Refusal response built for mode={mode_upper}")
    return base_response