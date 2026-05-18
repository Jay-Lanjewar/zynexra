from dataclasses import asdict, dataclass
from typing import Dict, List, Optional
import re

from backend.logger import logger
from backend.utils.pii import pre_redact_pii


@dataclass
class RedactionEntry:
    entity_type: str
    original_text: str
    replacement: str
    confidence: float
    start: int
    end: int

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class RedactionOptions:
    emails: bool = True
    phones: bool = True
    names: bool = True
    addresses: bool = True
    companies: bool = True


@dataclass
class RedactionResult:
    original_text: str
    redacted_text: str
    entities: List[RedactionEntry]
    fallback_used: bool = False

    def to_payload(self, model: str) -> Dict[str, object]:
        return {
            "success": True,
            "model": model,
            "mode": "REDACTION",
            "response_type": "redaction",
            "issue_count": 0,
            "issues": [],
            "structured_parse_failed": False,
            "legacy_text": self.redacted_text,
            "redacted_text": self.redacted_text,
            "original_text": self.original_text,
            "redaction_entities": [entity.to_dict() for entity in self.entities],
            "redaction_count": len(self.entities),
            "fallback_used": self.fallback_used,
        }


class RedactionEngine:
    ENTITY_PATTERNS = {
        "EMAIL": (
            re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
            0.99,
        ),
        "PHONE": (
            re.compile(r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}(?!\w)"),
            0.92,
        ),
        "ADDRESS": (
            re.compile(
                r"(?<![\d-])\b\d{1,6}\s+[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+){0,5}\s+"
                r"(?:Street|St|Road|Rd|Terrace|Avenue|Ave|Lane|Ln|Drive|Dr|Boulevard|Blvd|"
                r"Circle|Cir|Court|Ct|Way|Place|Pl)\b",
                re.IGNORECASE,
            ),
            0.9,
        ),
        "COMPANY": (
            re.compile(
                r"\b[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*){0,5}\s+"
                r"(?:Inc\.?|LLC|Ltd\.?|Limited|Corp\.?|Corporation|Company|Co\.?|LLP|PLC|Pvt\.?\s+Ltd\.?)\b"
            ),
            0.84,
        ),
        "MONEY": (
            re.compile(
                r"(?<!\w)(?:[$₹€£]\s?\d[\d,]*(?:\.\d{1,2})?|\d[\d,]*(?:\.\d{1,2})?\s?"
                r"(?:USD|INR|EUR|GBP|dollars?|rupees?|euros?|pounds?))(?!\w)",
                re.IGNORECASE,
            ),
            0.93,
        ),
        "DATE": (
            re.compile(
                r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
                r"\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
                r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4}|"
                r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4})\b",
                re.IGNORECASE,
            ),
            0.86,
        ),
        "ID_NUMBER": (
            re.compile(
                r"\b(?:[A-Z]{5}\d{4}[A-Z]|[A-Z]{2}\d{2}[A-Z0-9]{11}|"
                r"\d{3}-\d{2}-\d{4}|[A-Z]{1,4}[- ]?\d{5,12}|"
                r"(?:ID|Passport|Aadhaar|SSN|TIN|GSTIN|License)\s*(?:No\.?|Number|#)?\s*[:#-]?\s*[A-Z0-9-]{4,20})\b",
                re.IGNORECASE,
            ),
            0.82,
        ),
        "PERSON": (
            re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b"),
            0.72,
        ),
    }

    PRIORITY = {
        "EMAIL": 0,
        "PHONE": 1,
        "ADDRESS": 2,
        "COMPANY": 3,
        "MONEY": 4,
        "DATE": 5,
        "ID_NUMBER": 6,
        "PERSON": 7,
    }

    def redact(self, text: str, options: Optional[RedactionOptions] = None) -> RedactionResult:
        options = options or RedactionOptions()
        try:
            entities = self.detect_entities(text, options)
            redacted_text = self.apply_redactions(text, entities)
            return RedactionResult(
                original_text=text,
                redacted_text=redacted_text,
                entities=entities,
                fallback_used=False,
            )
        except Exception as e:
            logger.error("Structured redaction failed; falling back to regex masking. error=%s", e)
            return RedactionResult(
                original_text=text,
                redacted_text=pre_redact_pii(text),
                entities=[],
                fallback_used=True,
            )

    def detect_entities(self, text: str, options: RedactionOptions) -> List[RedactionEntry]:
        candidates: List[RedactionEntry] = []
        enabled = {
            "EMAIL": options.emails,
            "PHONE": options.phones,
            "PERSON": options.names,
            "ADDRESS": options.addresses,
            "COMPANY": options.companies,
            "MONEY": True,
            "DATE": True,
            "ID_NUMBER": True,
        }

        for entity_type, (pattern, confidence) in self.ENTITY_PATTERNS.items():
            if not enabled[entity_type]:
                continue
            for match in pattern.finditer(text):
                original = match.group(0)
                if entity_type == "PERSON" and self._looks_like_false_person(original):
                    continue
                candidates.append(
                    RedactionEntry(
                        entity_type=entity_type,
                        original_text=original,
                        replacement=f"[REDACTED_{entity_type}]",
                        confidence=confidence,
                        start=match.start(),
                        end=match.end(),
                    )
                )

        return self._dedupe_overlaps(candidates)

    def apply_redactions(self, text: str, entities: List[RedactionEntry]) -> str:
        redacted = text
        for entity in sorted(entities, key=lambda item: item.start, reverse=True):
            redacted = redacted[:entity.start] + entity.replacement + redacted[entity.end:]
        return redacted

    def _dedupe_overlaps(self, candidates: List[RedactionEntry]) -> List[RedactionEntry]:
        selected: List[RedactionEntry] = []
        occupied: List[range] = []
        ordered = sorted(
            candidates,
            key=lambda item: (self.PRIORITY[item.entity_type], -item.confidence, -(item.end - item.start), item.start),
        )

        for candidate in ordered:
            candidate_range = range(candidate.start, candidate.end)
            if any(self._ranges_overlap(candidate_range, existing) for existing in occupied):
                continue
            selected.append(candidate)
            occupied.append(candidate_range)

        return sorted(selected, key=lambda item: item.start)

    def _ranges_overlap(self, left: range, right: range) -> bool:
        return left.start < right.stop and right.start < left.stop

    def _looks_like_false_person(self, text: str) -> bool:
        false_tokens = {
            "Non Disclosure",
            "Confidential Information",
            "Effective Date",
            "Governing Law",
            "United States",
            "New York",
            "Los Angeles",
        }
        return text in false_tokens


def parse_redaction_options(values: Dict[str, object]) -> RedactionOptions:
    def parse_bool(value: object, default: bool = True) -> bool:
        if value is None:
            return default
        return str(value).strip().lower() not in {"0", "false", "no", "off"}

    return RedactionOptions(
        emails=parse_bool(values.get("redact_emails")),
        phones=parse_bool(values.get("redact_phones")),
        names=parse_bool(values.get("redact_names")),
        addresses=parse_bool(values.get("redact_addresses")),
        companies=parse_bool(values.get("redact_companies")),
    )
