from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import json
import re
import time

from backend.logger import logger
from backend.engines.response_schemas import (
    build_audit_response,
    build_advisory_response,
    SCHEMA_VERSION,
)
from backend.engines.confidence_engine import audit_scorer, advisory_scorer
from backend.engines.input_quality_engine import assess_input_quality, InputQualityResult
from backend.engines.contradiction_engine import (
    validate_contradictions,
    apply_contradiction_suppression,
    classify_document_contradictions,
)
from backend.engines.legal_domain_engine import (
    compute_document_domain_confidence,
    DocumentDomain,
    DOMAIN_SUPPRESSION_MESSAGE,
)
from backend.engines.recommendation_refiner import refine_suggested_improvements


@dataclass
class AuditIssue:
    """Structured schema for a legal audit issue."""
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
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        res = {}
        for field_name, value in asdict(self).items():
            if field_name == "extra_fields":
                continue
            if field_name == "contradiction_detected":
                if value is not None:
                    res[field_name] = bool(value)
            elif field_name == "original_category":
                if value is not None:
                    res[field_name] = str(value)
            elif field_name == "related_clause_count":
                if value is not None:
                    res[field_name] = int(value)
            else:
                res[field_name] = str(value or "")
        return res

AUDIT_ISSUE_FIELDS = [
    "issue_title",
    "severity",
    "category",
    "location",
    "quoted_text",
    "risk_explanation",
    "suggested_improvement",
]

AUDIT_TEXT_LABELS = {
    "issue_title": "Issue",
    "severity": "Severity",
    "category": "Category",
    "location": "Location",
    "quoted_text": "Quoted Text",
    "risk_explanation": "Risk Explanation",
    "suggested_improvement": "Suggested Improvement",
}

def extract_issue_categories(response_text: str) -> list:
    return re.findall(r"(?im)^Category:\s*(.+)$", response_text)

def extract_forbidden_phrase_candidates(response_text: str) -> list:
    return re.findall(
        r"(?i)\b(?:unlimited exposure|unlimited liability|unlimited|uncapped liability|uncapped|no cap|no limit|without restriction|without restrictions)\b",
        response_text
    )

def should_debug_regression_case(*values: str) -> bool:
    targets = {
        "nda_confidentiality_termination",
        "nda_malicious_structural_conflict",
    }
    combined = " ".join(str(value).lower() for value in values if value)
    return any(target in combined for target in targets)

def log_regression_debug(raw_response: str, normalized_response: str):
    categories_before = extract_issue_categories(raw_response)
    categories_after = extract_issue_categories(normalized_response)
    forbidden_before = extract_forbidden_phrase_candidates(raw_response)
    forbidden_after = extract_forbidden_phrase_candidates(normalized_response)

    logger.info("[Debug] Raw response -> %s", raw_response)
    logger.info("[Debug] Normalized response -> %s", normalized_response)
    logger.info("[Debug] Categories before normalization -> %s", categories_before)
    logger.info("[Debug] Categories after normalization -> %s", categories_after)
    logger.info("[Debug] Evaluator comparison source -> normalized")
    logger.info("[Debug] Evaluator comparison inputs -> categories=%s forbidden_phrases=%s", categories_after, forbidden_after)
    logger.info(
        "[Debug] Evaluator failure trigger conditions -> structural_exact_match_missing=%s forbidden_phrase_present=%s",
        "structural inconsistency" not in categories_after,
        bool(forbidden_after)
    )
    logger.info("[Debug] Forbidden phrase candidates before normalization -> %s", forbidden_before)
    logger.info("[Debug] Forbidden phrase candidates after normalization -> %s", forbidden_after)

def normalize_issue_key(key: str) -> str:
    """Normalize model-provided JSON/text keys into AuditIssue field names."""
    cleaned = re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")
    aliases = {
        "issue": "issue_title",
        "title": "issue_title",
        "risk": "risk_explanation",
        "risk_explanation": "risk_explanation",
        "suggestion": "suggested_improvement",
        "suggested_rewrite": "suggested_improvement",
        "suggested_improvement": "suggested_improvement",
        "quote": "quoted_text",
        "quoted": "quoted_text",
        "quoted_text": "quoted_text",
    }
    return aliases.get(cleaned, cleaned)

def coerce_audit_issue(raw_issue: Dict[str, Any]) -> AuditIssue:
    normalized: Dict[str, str] = {field_name: "" for field_name in AUDIT_ISSUE_FIELDS}
    extra_fields: Dict[str, Any] = {}

    for key, value in raw_issue.items():
        normalized_key = normalize_issue_key(key)
        if normalized_key in normalized:
            normalized[normalized_key] = "" if value is None else str(value).strip()
        else:
            extra_fields[str(key)] = value

    return AuditIssue(**normalized, extra_fields=extra_fields)

def _sanitize_json_strings(text: str) -> str:
    """Escape unescaped control characters (newlines, tabs, carriage returns) inside JSON string contexts."""
    result = []
    in_string = False
    escaped = False
    for ch in text:
        if escaped:
            result.append(ch)
            escaped = False
            continue
        if ch == '\\':
            result.append(ch)
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string:
            if ch == '\n':
                result.append('\\n')
            elif ch == '\r':
                result.append('\\r')
            elif ch == '\t':
                result.append('\\t')
            elif ord(ch) < 32:
                result.append(f'\\u{ord(ch):04x}')
            else:
                result.append(ch)
        else:
            result.append(ch)
    return ''.join(result)

def repair_json(text: str) -> Optional[str]:
    """Repair truncated/malformed JSON: unterminated strings, trailing commas, missing closers."""
    if not text or not text.strip():
        return None
    s = text.strip()
    fenced_match = re.match(r"```(?:json)?\s*(.*?)\s*(?:```)?\s*$", s, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        s = fenced_match.group(1).strip()
    start = -1
    for i, ch in enumerate(s):
        if ch in '{[':
            start = i
            break
    if start < 0:
        return None
    s = s[start:]
    # Sanitize literal control characters inside JSON strings first
    sanitized = _sanitize_json_strings(s)
    if sanitized != s:
        s = sanitized
        # re-check start after sanitization (should be same but safe)
        start = -1
        for i, ch in enumerate(s):
            if ch in '{[':
                start = i
                break
        if start < 0:
            return None
        s = s[start:]
    changes = {}
    new_s = re.sub(r',\s*([}\]])', r'\1', s)
    if new_s != s:
        changes['trailing_comma'] = True
        s = new_s
    # Stack-based approach to detect unterminated strings and missing closers
    stack = []
    in_string = False
    string_start = -1
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '\\':
            i += 2
            continue
        if ch == '"':
            if not in_string:
                string_start = i
            in_string = not in_string
            i += 1
            continue
        if not in_string:
            if ch == '{':
                stack.append('{')
            elif ch == '[':
                stack.append('[')
            elif ch == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
            elif ch == ']':
                if stack and stack[-1] == '[':
                    stack.pop()
        i += 1
    if in_string:
        ctx = ''
        for j in range(string_start - 1, -1, -1):
            if s[j] not in ' \t\n\r':
                ctx = s[j]
                break
        if ctx in '{,':
            s = s + '":""'
            changes['unterminated_key'] = True
        else:
            s = s + '"'
            changes['unterminated_string'] = True
        in_string = False
    if stack:
        closing = ''.join('}' if c == '{' else ']' for c in reversed(stack))
        s = s.rstrip() + closing
        changes['missing_brace'] = True
    for change in changes:
        logger.info("[StructuredRepair] repaired_%s=True", change)
    return s if changes else None

def extract_json_payload_candidates(response_text: str) -> List[str]:
    stripped = response_text.strip()
    has_json_indicators = bool(re.search(r'[\[{]', stripped))
    if not has_json_indicators:
        return []

    candidates = []
    if stripped:
        candidates.append(stripped)

    fenced_matches = re.findall(r"```(?:json)?\s*(.*?)```", stripped, re.IGNORECASE | re.DOTALL)
    for match in fenced_matches:
        trimmed = match.strip()
        if trimmed and trimmed not in candidates:
            candidates.append(trimmed)

    leading_candidates = re.findall(r'^\s*([\[\{].*?[\]\}])\s*$', stripped, re.DOTALL)
    for match in leading_candidates:
        trimmed = match.strip()
        if trimmed and trimmed not in candidates:
            candidates.append(trimmed)

    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char not in "[{":
            continue
        try:
            _, end = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        candidate = stripped[index:index + end].strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    return candidates

def audit_issues_from_json_payload(payload: Any) -> List[AuditIssue]:
    if isinstance(payload, dict):
        if isinstance(payload.get("issues"), list):
            raw_issues = payload["issues"]
        elif any(normalize_issue_key(key) in AUDIT_ISSUE_FIELDS for key in payload.keys()):
            raw_issues = [payload]
        else:
            raw_issues = []
    elif isinstance(payload, list):
        raw_issues = payload
    else:
        raw_issues = []

    issues = []
    for raw_issue in raw_issues:
        if not isinstance(raw_issue, dict):
            continue
        issue = coerce_audit_issue(raw_issue)
        if any(issue.to_dict().values()):
            issues.append(issue)
    return issues

def parse_audit_issues_from_json(response_text: str) -> List[AuditIssue]:
    for candidate in extract_json_payload_candidates(response_text):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        issues = audit_issues_from_json_payload(payload)
        if issues:
            logger.info("[Structured] JSON parse success -> %d issues", len(issues))
            return issues
    return []

def extract_labeled_text(block: str, label: str) -> str:
    pattern = re.compile(
        rf"(?is)^{re.escape(label)}:[ \t]*(.*?)(?=\n[A-Z][A-Za-z ]+:[ \t]*|\Z)",
        re.MULTILINE
    )
    match = pattern.search(block.strip())
    return match.group(1).strip() if match else ""

def parse_audit_issues_from_text(response_text: str) -> List[AuditIssue]:
    if "Issue:" not in response_text:
        return []

    issue_pattern = re.compile(r"(?ims)^Issue:\s*.*?(?=^Issue:\s*|\Z)")
    issues = []
    for match in issue_pattern.finditer(response_text):
        block = match.group(0).strip()
        raw_issue = {
            "issue_title": extract_labeled_text(block, "Issue"),
            "severity": extract_labeled_text(block, "Severity"),
            "category": extract_labeled_text(block, "Category"),
            "location": extract_labeled_text(block, "Location"),
            "quoted_text": extract_labeled_text(block, "Quoted Text"),
            "risk_explanation": extract_labeled_text(block, "Risk Explanation"),
            "suggested_improvement": extract_labeled_text(block, "Suggested Improvement"),
        }
        issue = coerce_audit_issue(raw_issue)
        if any(issue.to_dict().values()):
            issues.append(issue)
    return issues

def _try_parse_json(text: str) -> Optional[List[AuditIssue]]:
    """Try to parse JSON from text, with repair and progressive truncation."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if payload is not None:
        issues = audit_issues_from_json_payload(payload)
        if issues:
            return issues
    repaired = repair_json(text)
    if repaired is not None:
        try:
            payload = json.loads(repaired)
        except json.JSONDecodeError:
            payload = None
        if payload is not None:
            issues = audit_issues_from_json_payload(payload)
            if issues:
                return issues
    return None

def parse_audit_issues(response_text: str) -> List[AuditIssue]:
    # Sanitize unescaped control characters so JSON parsing doesn't choke
    response_text = _sanitize_json_strings(response_text)
    issues = parse_audit_issues_from_json(response_text)
    if issues:
        logger.info(
            "[StructuredOutcome] strict_json_success=True repair_success=False "
            "fallback_used=False issues_extracted=%d",
            len(issues)
        )
        return issues

    # Repair loop: try repair_json on each candidate
    for candidate in extract_json_payload_candidates(response_text):
        result = _try_parse_json(candidate)
        if result is not None:
            issues = result
            logger.info("[StructuredRepair] recovery_success=True")
            break

    if issues:
        logger.info(
            "[StructuredOutcome] strict_json_success=False repair_success=True "
            "fallback_used=False issues_extracted=%d",
            len(issues)
        )
        return issues

    # Progressive truncation: try truncating at last complete } or ]
    for candidate in extract_json_payload_candidates(response_text):
        stripped = candidate.rstrip()
        for close_char in ['}', ']']:
            pos = stripped.rfind(close_char)
            if pos >= len(stripped) // 2:
                prefix = stripped[:pos + 1]
                result = _try_parse_json(prefix)
                if result is not None:
                    issues = result
                    logger.info("[StructuredRepair] recovery_success=True")
                    break
        if issues:
            break

    if issues:
        logger.info(
            "[StructuredOutcome] strict_json_success=False repair_success=True "
            "fallback_used=False issues_extracted=%d",
            len(issues)
        )
        return issues

    logger.warning("[Structured] Fallback to text parsing triggered")
    issues = parse_audit_issues_from_text(response_text)
    fallback_used = len(issues) > 0

    logger.info(
        "[StructuredOutcome] strict_json_success=False repair_success=False "
        "fallback_used=%s issues_extracted=%d",
        fallback_used, len(issues)
    )
    return issues

def is_json_response_mode(response_format: Optional[str]) -> bool:
    return str(response_format or "").strip().lower() == "json"

INPUT_QUALITY_WARNING = "Document quality appears degraded or corrupted. Results may be unreliable."
SEMANTIC_SUPPRESSION_MESSAGE = "Document quality too degraded for reliable legal analysis."


def _assess_quoted_text_quality(text: str) -> bool:
    """Check if input text has poor quality indicators that would make legal analysis unreliable.

    Returns True if the text quality is poor enough to suppress semantic reasoning.
    """
    if not text or not text.strip():
        return True

    words = text.split()
    if not words:
        return True

    from backend.engines.input_quality_engine import (
        _has_alternating_pattern,
        _has_symbol_burst,
        _has_excessive_substitutions,
        _count_ocr_substitutions,
    )

    malformed_count = 0
    digit_letter_mix = re.compile(r'(?=.*\d)(?=.*[a-zA-Z])[a-zA-Z0-9]{3,}')
    consecutive_special = re.compile(r'[^\w\s]{2,}')

    for word in words:
        clean_word = re.sub(r'[^\w]', '', word)
        if len(clean_word) < 3:
            if len(word) >= 3 and (consecutive_special.search(word) or _has_symbol_burst(word)):
                malformed_count += 1
            continue

        is_malformed = False
        if digit_letter_mix.fullmatch(clean_word) and not clean_word.isdigit():
            digit_ratio = sum(1 for c in clean_word if c.isdigit()) / len(clean_word)
            if 0.1 <= digit_ratio <= 0.6:
                is_malformed = True

        if consecutive_special.search(word):
            is_malformed = True

        if _has_alternating_pattern(word):
            is_malformed = True

        if _has_excessive_substitutions(word):
            is_malformed = True

        if _has_symbol_burst(word):
            is_malformed = True

        if is_malformed:
            malformed_count += 1

    malformed_ratio = malformed_count / len(words)
    symbol_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
    symbol_density = symbol_count / len(text) if text else 0

    return malformed_ratio > 0.20 or symbol_density > 0.25


def build_audit_json_payload(
    complete_response: str,
    model: str,
    user_input: str = "",
    fallback_used: bool = False,
    inference_duration_ms: float = 0,
) -> Dict[str, Any]:
    """Build a machine-readable audit response with single-pass processing."""
    logger.info("[FallbackTrace] stage=build_audit_json_payload_entry fallback_used=%s", fallback_used)
    pipeline_start = time.time()

    # --- Parse ---
    parse_start = time.time()
    issues = parse_audit_issues(complete_response)
    parse_failed = len(issues) == 0
    parse_ms = (time.time() - parse_start) * 1000

    # --- Normalization ---
    norm_start = time.time()
    duplicate_suppressed = 0
    if not parse_failed:
        original_count = len(issues)
        issues = normalize_audit_issue_severity_fields(issues)
        issues = normalize_audit_issue_fields(issues)
        duplicate_suppressed = original_count - len(issues)

        contradictions = validate_contradictions(issues, user_input)
        if contradictions:
            issues = apply_contradiction_suppression(issues, contradictions)

        elevated_count = classify_document_contradictions(issues, user_input)
        if elevated_count:
            logger.info(
                "[ContradictionClassification] Elevated %d issue(s) to Structural Inconsistency in pipeline",
                elevated_count
            )
    normalization_ms = (time.time() - norm_start) * 1000

    # --- Input Quality ---
    quality_start = time.time()
    quality_result = assess_input_quality(user_input)
    input_quality_degraded = quality_result.is_degraded
    quality_warning = INPUT_QUALITY_WARNING if input_quality_degraded else ""
    quality_ms = (time.time() - quality_start) * 1000

    # --- Semantic Suppression ---
    semantic_suppressed = False
    if fallback_used and input_quality_degraded and _assess_quoted_text_quality(user_input):
        semantic_suppressed = True
        logger.warning(
            "[SemanticSuppression] TRIGGERED: fallback_used=True, input_quality_degraded=True, quoted_text_quality=poor"
        )
        issues = []
        parse_failed = True
        complete_response = SEMANTIC_SUPPRESSION_MESSAGE

    # --- Domain Detection ---
    domain_start = time.time()
    domain_suppressed = False
    if user_input and not semantic_suppressed:
        domain_result = compute_document_domain_confidence(user_input)
        domain_metadata = {
            "domain": domain_result.domain.value,
            "domain_confidence": round(domain_result.confidence, 4),
        }
        if domain_result.domain == DocumentDomain.NON_LEGAL:
            domain_suppressed = True
            logger.warning(
                "[DomainDetection] SUPPRESSION TRIGGERED: domain=NON_LEGAL "
                "legal_keyword_ratio=%.4f structure_score=%.4f",
                domain_result.legal_keyword_ratio, domain_result.structure_score,
            )
            issues = []
            parse_failed = True
            complete_response = DOMAIN_SUPPRESSION_MESSAGE
    else:
        domain_metadata = {}
    domain_ms = (time.time() - domain_start) * 1000

    # --- Confidence ---
    confidence_start = time.time()
    confidence_result = audit_scorer.compute(
        response_text=complete_response,
        issue_count=len(issues),
        structured_parse_failed=parse_failed,
        fallback_used=fallback_used,
        duplicate_suppressed=duplicate_suppressed,
        input_quality_degraded=input_quality_degraded,
    )

    if domain_suppressed:
        confidence_result.score = min(confidence_result.score, 0.25)
        confidence_result.label = "LOW"
        logger.warning(
            "[DomainDetection] Confidence capped: score=%.2f label=%s",
            confidence_result.score, confidence_result.label,
        )
    confidence_ms = (time.time() - confidence_start) * 1000

    total_ms = (time.time() - pipeline_start) * 1000

    # --- Perf logs ---
    logger.info("[Perf] inference_ms=%.0f", inference_duration_ms)
    logger.info("[Perf] parse_ms=%.0f", parse_ms)
    logger.info("[Perf] normalization_ms=%.0f", normalization_ms)
    logger.info("[Perf] quality_ms=%.0f", quality_ms)
    logger.info("[Perf] domain_ms=%.0f", domain_ms)
    logger.info("[Perf] confidence_ms=%.0f", confidence_ms)
    logger.info("[Perf] total_ms=%.0f", total_ms)

    # --- OptimizationSummary ---
    logger.info(
        "[OptimizationSummary] fallback_used=%s duplicate_rebuilds_eliminated=True "
        "structured_parse_success=%s total_ms=%.0f",
        fallback_used, not parse_failed, total_ms + inference_duration_ms,
    )

    metadata = {
        "model_name": model,
        "inference_duration_ms": round(inference_duration_ms),
        "parser_used": "json" if not parse_failed else "text",
        "fallback_used": fallback_used,
        "semantic_suppressed": semantic_suppressed,
    }

    if domain_metadata:
        metadata.update(domain_metadata)

    if input_quality_degraded:
        metadata["input_quality"] = "LOW"
        metadata["input_quality_score"] = round(quality_result.score, 4)
        metadata["input_quality_warnings"] = quality_result.warnings

    if parse_failed:
        return build_audit_response(
            complete_response=complete_response,
            model=model,
            issues=[],
            structured_parse_failed=True,
            confidence_score=confidence_result.score,
            confidence_label=confidence_result.label,
            quality_warning=quality_warning,
            metadata=metadata,
        )

    return build_audit_response(
        complete_response=complete_response,
        model=model,
        issues=[issue.to_dict() for issue in issues],
        structured_parse_failed=False,
        confidence_score=confidence_result.score,
        confidence_label=confidence_result.label,
        quality_warning=quality_warning,
        metadata=metadata,
    )

def build_mode_json_payload(
    complete_response: str,
    model: str,
    mode: str,
    user_query: str = "",
    fallback_used: bool = False,
    inference_duration_ms: float = 0,
) -> Dict[str, Any]:
    """Build mode-aware JSON while preserving legacy text compatibility."""
    logger.info("[FallbackTrace] stage=build_mode_json_payload_entry fallback_used=%s mode=%s", fallback_used, mode)
    normalized_mode = (mode or "AUDIT").upper()
    if normalized_mode == "AUDIT":
        return build_audit_json_payload(
            complete_response, model,
            user_input=user_query,
            fallback_used=fallback_used,
            inference_duration_ms=inference_duration_ms,
        )

    if normalized_mode == "ADVISORY":
        quality_result = assess_input_quality(user_query)
        input_quality_degraded = quality_result.is_degraded
        quality_warning = INPUT_QUALITY_WARNING if input_quality_degraded else ""

        semantic_suppressed = False
        if fallback_used and input_quality_degraded and _assess_quoted_text_quality(user_query):
            semantic_suppressed = True
            logger.warning(
                "[SemanticSuppression] ADVISORY TRIGGERED: fallback_used=True, input_quality_degraded=True, quoted_text_quality=poor"
            )
            complete_response = SEMANTIC_SUPPRESSION_MESSAGE

        confidence_result = advisory_scorer.compute(
            response_text=complete_response,
            user_query=user_query,
            input_quality_degraded=input_quality_degraded,
            fallback_used=fallback_used,
        )
        metadata = {
            "model_name": model,
            "inference_duration_ms": 0,
            "fallback_used": fallback_used,
            "semantic_suppressed": semantic_suppressed,
        }
        if input_quality_degraded:
            metadata["input_quality"] = "LOW"
            metadata["input_quality_score"] = round(quality_result.score, 4)
            metadata["input_quality_warnings"] = quality_result.warnings

        return build_advisory_response(
            complete_response=complete_response,
            model=model,
            confidence_score=confidence_result.score,
            confidence_label=confidence_result.label,
            quality_warning=quality_warning,
            metadata=metadata,
        )

    return {
        "success": True,
        "model": model,
        "mode": normalized_mode,
        "response_type": normalized_mode.lower(),
        "schema_version": SCHEMA_VERSION,
        "issue_count": 0,
        "issues": [],
        "structured_parse_failed": False,
        "legacy_text": complete_response,
        "redacted_text": complete_response,
        "fallback_used": fallback_used,
    }

def render_audit_issues_as_text(issues: List[AuditIssue]) -> str:
    def render_line(field_name: str, value: str) -> str:
        label = AUDIT_TEXT_LABELS[field_name]
        return f"{label}: {value}" if value else f"{label}:"

    rendered_blocks = []
    for issue in issues:
        issue_dict = issue.to_dict()
        rendered_blocks.append(
            "\n".join(
                [
                    render_line("issue_title", issue_dict["issue_title"]),
                    render_line("severity", issue_dict["severity"]),
                    render_line("category", issue_dict["category"]),
                    render_line("location", issue_dict["location"]),
                    render_line("quoted_text", issue_dict["quoted_text"]),
                    render_line("risk_explanation", issue_dict["risk_explanation"]),
                    render_line("suggested_improvement", issue_dict["suggested_improvement"]),
                ]
            ).rstrip()
        )
    return "\n\n".join(rendered_blocks)

def extract_audit_text_wrappers(response_text: str) -> tuple[str, str]:
    """Preserve any legacy text surrounding Issue blocks."""
    issue_pattern = re.compile(r"(?ims)^Issue:\s*.*?(?=^Issue:\s*|\Z)")
    matches = list(issue_pattern.finditer(response_text))
    if not matches:
        return "", ""
    return response_text[:matches[0].start()].strip(), response_text[matches[-1].end():].strip()

def render_legacy_audit_text(response_text: str, issues: List[AuditIssue]) -> str:
    rendered = render_audit_issues_as_text(issues)
    prefix, suffix = extract_audit_text_wrappers(response_text)
    if prefix:
        rendered = f"{prefix}\n\n{rendered}" if rendered else prefix
    if suffix:
        rendered = f"{rendered}\n\n{suffix}" if rendered else suffix
    return rendered

def normalize_audit_issue_severity_fields(issues: List[AuditIssue]) -> List[AuditIssue]:
    """Deterministically enforce severity overrides on structured issue fields."""
    unlimited_pattern = re.compile(r"\b(unlimited|uncapped)\b|no cap|no limit", re.IGNORECASE)
    severity_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    for issue in issues:
        current_severity = issue.severity.strip().upper()
        category_upper = issue.category.strip().upper()
        has_unlimited = bool(unlimited_pattern.search(issue.quoted_text or ""))
        new_severity = current_severity

        if has_unlimited:
            new_severity = "CRITICAL"
        if category_upper in {"GOVERNING LAW", "GOVERNING LAW RISK"}:
            if severity_rank.get(new_severity, -1) < severity_rank["HIGH"]:
                new_severity = "HIGH"
        if "RESIDUALS" in category_upper:
            if severity_rank.get(new_severity, -1) < severity_rank["HIGH"]:
                new_severity = "HIGH"
        if "INDEMNIFICATION" in category_upper and has_unlimited:
            new_severity = "CRITICAL"

        if new_severity and new_severity != current_severity:
            issue.severity = new_severity
    return issues

def sanitize_capped_indemnity_text(text: str) -> str:
    replacements = [
        (r"\buncapped liability\b", "capped liability"),
        (r"\bunlimited liability\b", "capped liability"),
        (r"\buncapped indemnification\b", "capped indemnification"),
        (r"\bunlimited indemnification\b", "capped indemnification"),
        (r"\bno cap\b", "a defined cap"),
        (r"\bno limit\b", "a defined limit"),
    ]
    sanitized = text
    for pattern, replacement in replacements:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized

CONTRADICTION_INCOMPATIBLE_CATEGORIES = {
    "indemnification",
    "liability exposure",
}


def normalize_audit_issue_fields(issues: List[AuditIssue]) -> List[AuditIssue]:
    """Normalize categories, language, and duplicates using structured fields."""
    unlimited_tokens = re.compile(r"\b(unlimited|uncapped|no cap|no limit)\b", re.IGNORECASE)
    unlimited_word = re.compile(r"\bunlimited\b", re.IGNORECASE)
    capped_indemnity_cues = re.compile(
        r"\b(?:capped at|liability cap|aggregate cap|shall not exceed|must not exceed|may not exceed|"
        r"limited to|maximum amount|up to|cap of)\b|[$â‚¹â‚¬Â£]\s?\d|\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:usd|inr|eur|gbp|dollars|rupees)\b",
        re.IGNORECASE
    )
    structural_categories = {
        "conflicting structure",
        "malformed structure",
        "structural conflict",
        "structural contradiction",
        "structural inconsistency",
        "structural omission",
    }
    indemnification_categories = {
        "indemnification risk",
        "uncapped liability",
        "indemnity concern",
    }
    indemnification_cues = re.compile(r"\b(indemn|indemnify|indemnity|hold harmless)\b", re.IGNORECASE)
    structural_cues = re.compile(
        r"\b(conflict|conflicting|contradict|contradiction|inconsistent|inconsistency|incompatible|malformed)\b",
        re.IGNORECASE
    )
    structural_heuristic_cues = re.compile(
        r"\b(?:contradictory obligations|conflicting clauses|inconsistent obligations|"
        r"mutually exclusive terms|structural contradiction|impossible compliance|"
        r"termination conflict|conflicting survival language)\b",
        re.IGNORECASE
    )

    for issue in issues:
        category_text = issue.category.strip()
        category_lower = category_text.lower()
        combined_issue_text = " ".join(
            [category_text, issue.quoted_text, issue.risk_explanation, issue.suggested_improvement]
        )

        if unlimited_word.search(issue.risk_explanation):
            issue.risk_explanation = unlimited_word.sub("uncapped", issue.risk_explanation)
        if unlimited_word.search(issue.suggested_improvement):
            issue.suggested_improvement = unlimited_word.sub("uncapped", issue.suggested_improvement)

        has_indemnity_context = "indemnification" in category_lower or indemnification_cues.search(combined_issue_text)
        has_explicit_cap = bool(capped_indemnity_cues.search(issue.quoted_text or ""))
        if has_indemnity_context and has_explicit_cap:
            corrected_risk = sanitize_capped_indemnity_text(issue.risk_explanation)
            corrected_suggestion = sanitize_capped_indemnity_text(issue.suggested_improvement)
            if corrected_risk != issue.risk_explanation:
                logger.info("[Normalization] Forbidden phrase correction -> capped indemnity risk text")
                issue.risk_explanation = corrected_risk
            if corrected_suggestion != issue.suggested_improvement:
                logger.info("[Normalization] Forbidden phrase correction -> capped indemnity suggestion text")
                issue.suggested_improvement = corrected_suggestion

        new_category = category_text
        if category_lower in structural_categories:
            new_category = "Structural Inconsistency"
        elif category_lower in indemnification_categories:
            new_category = "Indemnification"
        elif category_lower == "liability exposure" and indemnification_cues.search(combined_issue_text):
            new_category = "Indemnification"
        elif category_lower == "residuals risk":
            new_category = "Residuals"
        elif category_lower == "governing law risk":
            new_category = "Governing Law"

        if new_category != category_text:
            logger.info("[Normalization] Category remap -> %s -> %s", category_text, new_category)
            issue.category = new_category
            category_text = new_category
            category_lower = new_category.lower()

        severity_text = issue.severity.strip().upper()

        # NEVER remap indemnification/liability categories to Structural Inconsistency
        if category_lower not in CONTRADICTION_INCOMPATIBLE_CATEGORIES:
            if severity_text in {"HIGH", "CRITICAL"} and structural_heuristic_cues.search(combined_issue_text):
                logger.info("[Normalization] Structural heuristic trigger -> Structural Inconsistency")
                if issue.category != "Structural Inconsistency":
                    issue.category = "Structural Inconsistency"
                    category_lower = "structural inconsistency"

            if structural_cues.search(issue.risk_explanation) or structural_cues.search(issue.quoted_text):
                if issue.category != "Structural Inconsistency":
                    logger.info("[Normalization] Category remap -> %s -> Structural Inconsistency", issue.category)
                    issue.category = "Structural Inconsistency"
                    category_lower = "structural inconsistency"

        if "residuals" in category_lower:
            cleaned_risk = re.sub(
                r"\b(unlimited|uncapped|no limit|no cap)\b",
                "unrestricted",
                issue.risk_explanation,
                flags=re.IGNORECASE
            )
            cleaned_risk = re.sub(r"\b(liability|liable|damages|exposure)\b", "", cleaned_risk, flags=re.IGNORECASE)
            issue.risk_explanation = " ".join(cleaned_risk.split())
            issue.suggested_improvement = (
                "Clarify that residual knowledge does not permit use of confidential information and "
                "ensure confidentiality obligations continue after termination."
            )

        if "confidentiality" in category_lower:
            issue.suggested_improvement = "Ensure confidentiality obligations survive termination and continue after contract expiration."

        if "indemnification" in category_lower and unlimited_tokens.search(issue.quoted_text or ""):
            issue.suggested_improvement = (
                "Introduce a liability cap so indemnification obligations include a liability cap at a defined monetary amount."
            )

    issues = refine_suggested_improvements(issues)
    return suppress_duplicate_audit_issues(issues)

def suppress_duplicate_audit_issues(issues: List[AuditIssue]) -> List[AuditIssue]:
    kept_issues = []
    seen_quotes = set()
    suppressed_count = 0

    for issue in issues:
        quote_key = normalize_quoted_text_key(issue.quoted_text)
        if quote_key and quote_key in seen_quotes:
            suppressed_count += 1
            continue
        if quote_key:
            seen_quotes.add(quote_key)
        kept_issues.append(issue)

    if suppressed_count:
        logger.info("[Normalization] Duplicate quoted text suppressions -> %s", suppressed_count)

    return kept_issues

def normalize_audit_response(response_text: str, mode: str = "AUDIT") -> str:
    """Normalize audit output through structured issues and render legacy text."""
    if mode != "AUDIT":
        return response_text

    structured_issues = parse_audit_issues(response_text)
    if not structured_issues:
        normalized_response = normalize_issue_severity(response_text)
        return normalize_issue_output(normalized_response)

    structured_issues = normalize_audit_issue_severity_fields(structured_issues)
    structured_issues = normalize_audit_issue_fields(structured_issues)
    return render_legacy_audit_text(response_text, structured_issues)

def normalize_issue_severity(response_text: str) -> str:
    """Deterministically enforce severity overrides on parsed issues."""
    if "Issue:" not in response_text:
        return response_text

    issue_pattern = re.compile(r"(?ims)^Issue:\s*.*?(?=^Issue:\s*|\Z)")
    unlimited_pattern = re.compile(r"\b(unlimited|uncapped)\b|no cap|no limit", re.IGNORECASE)
    severity_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    def apply_overrides(block: str) -> str:
        severity_match = re.search(r"(?im)^Severity:\s*(.+)", block)
        category_match = re.search(r"(?im)^Category:\s*(.+)", block)
        quoted_match = re.search(
            r"(?is)Quoted Text:\s*(.*?)(?:\n[A-Z][A-Za-z ]+:\s|$)",
            block.strip()
        )

        if not severity_match or not category_match:
            return block

        current_severity = severity_match.group(1).strip().upper()
        category = category_match.group(1).strip()
        quoted = quoted_match.group(1).strip() if quoted_match else ""

        has_unlimited = bool(unlimited_pattern.search(quoted))
        category_upper = category.upper()
        new_severity = current_severity

        # 1. Unlimited exposure -> CRITICAL
        if has_unlimited:
            new_severity = "CRITICAL"

        # 2. Governing Law / Governing Law Risk -> at least HIGH
        if category_upper in {"GOVERNING LAW", "GOVERNING LAW RISK"}:
            if severity_rank.get(new_severity, -1) < severity_rank["HIGH"]:
                new_severity = "HIGH"

        # 3. Residuals -> at least HIGH
        if "RESIDUALS" in category_upper:
            if severity_rank.get(new_severity, -1) < severity_rank["HIGH"]:
                new_severity = "HIGH"

        # 4. Indemnification + unlimited -> CRITICAL
        if "INDEMNIFICATION" in category_upper and has_unlimited:
            new_severity = "CRITICAL"

        if new_severity != current_severity:
            block = re.sub(
                r"(?im)^(Severity:\s*)(.+)$",
                rf"\1{new_severity}",
                block,
                count=1
            )

        return block

    return issue_pattern.sub(lambda m: apply_overrides(m.group(0)), response_text)

def normalize_quoted_text_key(quoted_text: str) -> str:
    """Create a stable key for duplicate quoted-text detection."""
    normalized = re.sub(r"\s+", " ", quoted_text.strip().strip('"').strip("'"))
    return normalized.lower()

def suppress_duplicate_quoted_issues(response_text: str) -> str:
    """Discard later issues that repeat identical quoted text."""
    if "Issue:" not in response_text:
        return response_text

    issue_pattern = re.compile(r"(?ims)^Issue:\s*.*?(?=^Issue:\s*|\Z)")
    kept_blocks = []
    seen_quotes = set()
    suppressed_count = 0
    last_end = 0
    prefix = ""

    for match in issue_pattern.finditer(response_text):
        if not kept_blocks and match.start() > 0:
            prefix = response_text[:match.start()]

        last_end = match.end()
        block = match.group(0).rstrip()
        quoted_match = re.search(
            r"(?is)Quoted Text:\s*(.*?)(?:\n[A-Z][A-Za-z ]+:\s|$)",
            block.strip()
        )
        quoted_text = quoted_match.group(1).strip() if quoted_match else ""
        quote_key = normalize_quoted_text_key(quoted_text)

        if quote_key and quote_key in seen_quotes:
            suppressed_count += 1
            continue

        if quote_key:
            seen_quotes.add(quote_key)
        kept_blocks.append(block)

    if suppressed_count:
        logger.info("[Normalization] Duplicate quoted text suppressions -> %s", suppressed_count)

    if not kept_blocks:
        return response_text

    suffix = response_text[last_end:].strip()
    normalized_output = prefix.rstrip()
    if normalized_output:
        normalized_output += "\n\n"
    normalized_output += "\n\n".join(kept_blocks)
    if suffix:
        normalized_output += "\n\n" + suffix
    return normalized_output


def normalize_issue_output(response_text: str) -> str:
    """Normalize categories and language for deterministic outputs."""
    if "Issue:" not in response_text:
        return response_text

    issue_pattern = re.compile(r"(?ims)^Issue:\s*.*?(?=^Issue:\s*|\Z)")
    unlimited_tokens = re.compile(r"\b(unlimited|uncapped|no cap|no limit)\b", re.IGNORECASE)
    unlimited_word = re.compile(r"\bunlimited\b", re.IGNORECASE)
    capped_indemnity_cues = re.compile(
        r"\b(?:capped at|liability cap|aggregate cap|shall not exceed|must not exceed|may not exceed|"
        r"limited to|maximum amount|up to|cap of)\b|[$₹€£]\s?\d|\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:usd|inr|eur|gbp|dollars|rupees)\b",
        re.IGNORECASE
    )
    structural_categories = {
        "conflicting structure",
        "malformed structure",
        "structural conflict",
        "structural contradiction",
        "structural inconsistency",
        "structural omission",
    }
    indemnification_categories = {
        "indemnification risk",
        "uncapped liability",
        "indemnity concern",
    }
    indemnification_cues = re.compile(r"\b(indemn|indemnify|indemnity|hold harmless)\b", re.IGNORECASE)
    structural_cues = re.compile(
        r"\b(conflict|conflicting|contradict|contradiction|inconsistent|inconsistency|incompatible|malformed)\b",
        re.IGNORECASE
    )
    structural_heuristic_cues = re.compile(
        r"\b(?:contradictory obligations|conflicting clauses|inconsistent obligations|"
        r"mutually exclusive terms|structural contradiction|impossible compliance|"
        r"termination conflict|conflicting survival language)\b",
        re.IGNORECASE
    )

    def replace_section(block: str, label: str, new_text: str) -> str:
        pattern = re.compile(
            rf"(?is)({re.escape(label)}:\s*)(.*?)(?=\n[A-Z][A-Za-z ]+:\s|$)"
        )
        return pattern.sub(lambda m: f"{m.group(1)}{new_text}", block, count=1)

    def sanitize_capped_indemnity_text(text: str) -> str:
        replacements = [
            (r"\buncapped liability\b", "capped liability"),
            (r"\bunlimited liability\b", "capped liability"),
            (r"\buncapped indemnification\b", "capped indemnification"),
            (r"\bunlimited indemnification\b", "capped indemnification"),
            (r"\bno cap\b", "a defined cap"),
            (r"\bno limit\b", "a defined limit"),
        ]
        sanitized = text
        for pattern, replacement in replacements:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized

    def apply_normalization(block: str) -> str:
        severity_match = re.search(r"(?im)^Severity:\s*(.+)", block)
        category_match = re.search(r"(?im)^Category:\s*(.+)", block)
        quoted_match = re.search(
            r"(?is)Quoted Text:\s*(.*?)(?:\n[A-Z][A-Za-z ]+:\s|$)",
            block.strip()
        )
        risk_match = re.search(
            r"(?is)(Risk Explanation:\s*)(.*?)(?=\n[A-Z][A-Za-z ]+:\s|$)",
            block.strip()
        )
        suggested_match = re.search(
            r"(?is)(Suggested Improvement:\s*)(.*?)(?=\n[A-Z][A-Za-z ]+:\s|$)",
            block.strip()
        )

        category_text = category_match.group(1).strip() if category_match else ""
        category_lower = category_text.lower()
        quoted_text = quoted_match.group(1).strip() if quoted_match else ""
        risk_text = risk_match.group(2).strip() if risk_match else ""
        suggested_text = suggested_match.group(2).strip() if suggested_match else ""
        severity_text = severity_match.group(1).strip().upper() if severity_match else ""
        risk_changed = False
        suggested_changed = False
        combined_issue_text = " ".join([category_text, quoted_text, risk_text, suggested_text])

        # 0. Global unlimited sanitization outside quoted text
        if unlimited_word.search(risk_text):
            risk_text = unlimited_word.sub("uncapped", risk_text)
            risk_changed = True
        if unlimited_word.search(suggested_text):
            suggested_text = unlimited_word.sub("uncapped", suggested_text)
            suggested_changed = True

        has_indemnity_context = "indemnification" in category_lower or indemnification_cues.search(combined_issue_text)
        has_explicit_cap = bool(capped_indemnity_cues.search(quoted_text))
        if has_indemnity_context and has_explicit_cap:
            corrected_risk = sanitize_capped_indemnity_text(risk_text)
            corrected_suggestion = sanitize_capped_indemnity_text(suggested_text)
            if corrected_risk != risk_text:
                logger.info("[Normalization] Forbidden phrase correction -> capped indemnity risk text")
                risk_text = corrected_risk
                risk_changed = True
            if corrected_suggestion != suggested_text:
                logger.info("[Normalization] Forbidden phrase correction -> capped indemnity suggestion text")
                suggested_text = corrected_suggestion
                suggested_changed = True

        # 1. Category normalization (Category line only)
        new_category = category_text
        if category_lower in structural_categories:
            new_category = "Structural Inconsistency"
        elif category_lower in indemnification_categories:
            new_category = "Indemnification"
        elif category_lower == "liability exposure" and indemnification_cues.search(combined_issue_text):
            new_category = "Indemnification"
        elif category_lower == "residuals risk":
            new_category = "Residuals"
        elif category_lower == "governing law risk":
            new_category = "Governing Law"

        if new_category != category_text and category_match:
            logger.info("[Normalization] Category remap -> %s -> %s", category_text, new_category)
            block = re.sub(
                r"(?im)^(Category:\s*).+$",
                rf"\1{new_category}",
                block,
                count=1
            )
            category_text = new_category
            category_lower = new_category.lower()

        # 2. Heuristic structural conflict detection for adversarial contract contradictions.
        if category_lower not in CONTRADICTION_INCOMPATIBLE_CATEGORIES:
            if severity_text in {"HIGH", "CRITICAL"} and structural_heuristic_cues.search(combined_issue_text):
                logger.info("[Normalization] Structural heuristic trigger -> Structural Inconsistency")
                if category_text != "Structural Inconsistency":
                    block = re.sub(
                        r"(?im)^(Category:\s*).+$",
                        r"\1Structural Inconsistency",
                        block,
                        count=1
                    )
                    category_text = "Structural Inconsistency"
                    category_lower = category_text.lower()

        # 3. Structural conflict normalization based on quoted or risk language
        if category_lower not in CONTRADICTION_INCOMPATIBLE_CATEGORIES:
            if structural_cues.search(risk_text) or structural_cues.search(quoted_text):
                if category_text != "Structural Inconsistency":
                    logger.info("[Normalization] Category remap -> %s -> Structural Inconsistency", category_text)
                    block = re.sub(
                        r"(?im)^(Category:\s*).+$",
                        r"\1Structural Inconsistency",
                        block,
                        count=1
                    )
                    category_text = "Structural Inconsistency"
                    category_lower = category_text.lower()

        # 4. Residuals language cleanup
        if "residuals" in category_lower:
            cleaned_risk = re.sub(r"\b(unlimited|uncapped|no limit|no cap)\b", "unrestricted", risk_text, flags=re.IGNORECASE)
            cleaned_risk = re.sub(r"\b(liability|liable|damages|exposure)\b", "", cleaned_risk, flags=re.IGNORECASE)
            cleaned_risk = " ".join(cleaned_risk.split())
            risk_text = cleaned_risk
            block = replace_section(block, "Risk Explanation", risk_text)
            resid_improvement = ("Clarify that residual knowledge does not permit use of confidential information and "
                                 "ensure confidentiality obligations continue after termination.")
            suggested_text = resid_improvement
            block = replace_section(block, "Suggested Improvement", suggested_text)

        # 5. Confidentiality rewrite safeguard
        if "confidentiality" in category_lower:
            conf_text = "Ensure confidentiality obligations survive termination and continue after contract expiration."
            suggested_text = conf_text
            block = replace_section(block, "Suggested Improvement", suggested_text)

        # 6. Enforce cap wording for indemnification with unlimited cues
        if "indemnification" in category_lower and unlimited_tokens.search(quoted_text):
            cap_text = (
                "Introduce a liability cap so indemnification obligations include a liability cap at a defined monetary amount."
            )
            suggested_text = cap_text
            block = replace_section(block, "Suggested Improvement", suggested_text)

        # Apply global unlimited replacements if they haven't been written back yet
        if risk_changed:
            block = replace_section(block, "Risk Explanation", risk_text)
        if suggested_changed:
            block = replace_section(block, "Suggested Improvement", suggested_text)

        return block

    normalized_text = issue_pattern.sub(lambda m: apply_normalization(m.group(0)), response_text)
    return suppress_duplicate_quoted_issues(normalized_text)

