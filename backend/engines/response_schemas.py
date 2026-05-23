from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from enum import Enum

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

    if not validate_audit_response(response_dict):
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