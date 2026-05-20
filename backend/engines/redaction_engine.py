from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple
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
    PERSON_EXCLUSIONS = {
        "Agreement",
        "Recipient",
        "Discloser",
        "Company",
        "Corporation",
        "Clause",
        "Section",
        "Exhibit",
        "Schedule",
        "Governing Law",
        "Cayman Islands",
        "New York",
        "San Francisco",
        "Austin",
        "Disclosure Agreement",
        "This Agreement",
        "The Recipient",
    }
    LEGAL_TERMS = {
        "agreement",
        "clause",
        "confidential",
        "confidentiality",
        "disclosure",
        "discloser",
        "effective",
        "exhibit",
        "governing",
        "jurisdiction",
        "law",
        "party",
        "recipient",
        "schedule",
        "section",
        "term",
    }
    COMPANY_INDICATORS = {
        "llc",
        "inc",
        "ltd",
        "limited",
        "corp",
        "corporation",
        "company",
        "co",
        "services",
        "solutions",
        "group",
        "holdings",
    }
    LOCATION_TERMS = {
        "Austin",
        "California",
        "Canada",
        "Cayman Islands",
        "Delaware",
        "England",
        "Florida",
        "France",
        "Germany",
        "India",
        "Ireland",
        "London",
        "New York",
        "San Francisco",
        "Singapore",
        "Texas",
        "United Kingdom",
        "United States",
    }
    LEGAL_TEMPLATE_PATTERNS = (
        re.compile(r"\b(?:this|the)\s+(?:agreement|recipient|discloser|company|clause|section|exhibit|schedule)\b", re.IGNORECASE),
        re.compile(r"\b(?:non[-\s]?disclosure|confidentiality|disclosure)\s+agreement\b", re.IGNORECASE),
        re.compile(r"\bgoverning\s+law\b", re.IGNORECASE),
    )

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
                r"(?:Inc\.?|LLC|Ltd\.?|Limited|Corp\.?|Corporation|Company|Co\.?|LLP|PLC|"
                r"Pvt\.?\s+Ltd\.?|Services|Solutions|Group|Holdings)\b"
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
        "LOCATION": (
            re.compile(
                r"\b(?:Austin|California|Canada|Cayman Islands|Delaware|England|Florida|France|Germany|"
                r"India|Ireland|London|New York|San Francisco|Singapore|Texas|United Kingdom|United States)\b"
            ),
            0.78,
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
        "LOCATION": 7,
        "PERSON": 8,
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
            "LOCATION": options.names,
        }

        for entity_type, (pattern, confidence) in self.ENTITY_PATTERNS.items():
            if not enabled[entity_type]:
                continue
            for match in pattern.finditer(text):
                original = match.group(0)
                candidate_type = entity_type
                candidate_confidence = self._adjust_confidence(entity_type, original, text, match.start(), confidence)
                if entity_type == "PERSON":
                    candidate_type, candidate_confidence, rejection_reason = self._classify_person_candidate(
                        original,
                        text,
                        match.start(),
                        match.end(),
                        candidate_confidence,
                    )
                    if rejection_reason:
                        self._log_rejected_person(original, rejection_reason)
                        continue
                candidates.append(
                    RedactionEntry(
                        entity_type=candidate_type,
                        original_text=original,
                        replacement=f"[REDACTED_{candidate_type}]",
                        confidence=candidate_confidence,
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

    def _classify_person_candidate(
        self,
        candidate: str,
        full_text: str,
        start: int,
        end: int,
        confidence: float,
    ) -> Tuple[str, float, Optional[str]]:
        if candidate in self.PERSON_EXCLUSIONS:
            return "PERSON", confidence, "excluded term"
        if self._is_location(candidate):
            return "LOCATION", max(confidence - 0.08, 0.5), None
        if self._has_this_or_the_context(candidate, full_text, start):
            return "PERSON", confidence, "This/The legal reference"
        if self._contains_legal_document_terminology(candidate):
            return "PERSON", confidence, "legal document terminology"
        if self._is_all_caps_organization(candidate):
            return "PERSON", confidence, "all-uppercase organization pattern"
        if self._appears_in_legal_clause_template(full_text, start, end):
            return "PERSON", confidence, "legal clause template"
        if self._has_company_context(candidate, full_text, start, end):
            return "COMPANY", max(confidence, 0.82), None
        if confidence < 0.45:
            return "PERSON", confidence, "low confidence after boilerplate penalties"
        return "PERSON", confidence, None

    def _adjust_confidence(self, entity_type: str, candidate: str, full_text: str, start: int, confidence: float) -> float:
        adjusted = confidence
        normalized = candidate.lower()
        if entity_type == "PERSON" and any(term in normalized for term in self.LEGAL_TERMS):
            adjusted -= 0.18
        if entity_type == "PERSON" and self._appears_in_legal_clause_template(full_text, start, start + len(candidate)):
            adjusted -= 0.16
        if entity_type == "PERSON" and full_text.lower().count(normalized) > 1 and any(term in normalized for term in self.LEGAL_TERMS):
            adjusted -= 0.12
        if entity_type == "PERSON" and self._is_boilerplate_context(full_text, start, start + len(candidate)):
            adjusted -= 0.1
        return max(round(adjusted, 2), 0.0)

    def _is_location(self, candidate: str) -> bool:
        return candidate in self.LOCATION_TERMS

    def _has_this_or_the_context(self, candidate: str, full_text: str, start: int) -> bool:
        words = candidate.split()
        if words and words[0] in {"This", "The"}:
            return True
        prefix = full_text[max(0, start - 12):start]
        return bool(re.search(r"\b(?:This|The)\s+$", prefix))

    def _contains_legal_document_terminology(self, candidate: str) -> bool:
        normalized_words = {word.lower().strip(".,:;()[]") for word in candidate.split()}
        return bool(normalized_words & self.LEGAL_TERMS)

    def _is_all_caps_organization(self, candidate: str) -> bool:
        return bool(re.search(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b", candidate))

    def _appears_in_legal_clause_template(self, full_text: str, start: int, end: int) -> bool:
        window = full_text[max(0, start - 24):min(len(full_text), end + 24)]
        return any(pattern.search(window) for pattern in self.LEGAL_TEMPLATE_PATTERNS)

    def _has_company_context(self, candidate: str, full_text: str, start: int, end: int) -> bool:
        normalized_words = {word.lower().strip(".,:;()[]") for word in candidate.split()}
        if normalized_words & self.COMPANY_INDICATORS:
            return True
        nearby = full_text[max(0, start - 20):min(len(full_text), end + 20)].lower()
        return any(re.search(rf"\b{re.escape(indicator)}\.?\b", nearby) for indicator in self.COMPANY_INDICATORS)

    def _is_boilerplate_context(self, full_text: str, start: int, end: int) -> bool:
        nearby = full_text[max(0, start - 36):min(len(full_text), end + 36)].lower()
        boilerplate_terms = ("whereas", "hereby", "pursuant", "notwithstanding", "set forth", "governing law")
        return any(term in nearby for term in boilerplate_terms)

    def _log_rejected_person(self, candidate: str, reason: str) -> None:
        logger.debug("[Redaction] Rejected PERSON candidate -> %s (%s)", candidate, reason)


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
