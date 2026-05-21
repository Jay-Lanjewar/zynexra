from dataclasses import dataclass, field
from typing import Any, Dict, List
import re
import math

from backend.logger import logger


COMMON_ENGLISH_WORDS = frozenset({
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
    "people", "into", "year", "your", "good", "some", "could", "them", "see", "other",
    "than", "then", "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first", "well", "way",
    "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
    "is", "are", "was", "were", "been", "has", "had", "did", "does", "done",
    "shall", "may", "must", "should", "might", "will", "would", "could", "can",
    "contract", "agreement", "party", "parties", "terms", "condition", "liability",
    "indemnification", "termination", "confidential", "breach", "damages", "jurisdiction",
    "arbitration", "compliance", "regulation", "statute", "obligation", "warranty",
    "disclaimer", "intellectual", "property", "copyright", "trademark", "patent",
    "employment", "severance", "non-compete", "non-solicit", "clause", "section",
    "article", "provision", "effective", "date", "execution", "performance",
    "representations", "covenants", "indemnify", "hold", "harmless", "liable",
    "negligence", "gross", "willful", "misconduct", "force", "majeure", "act",
    "god", "notice", "assignment", "delegation", "successors", "assigns",
    "governing", "law", "venue", "dispute", "resolution", "mediation",
    "severability", "waiver", "amendment", "modification", "entire",
    "integration", "counterparts", "facsimile", "electronic", "signature",
    "binding", "enforceable", "valid", "void", "voidable", "null",
    "residuals", "knowledge", "skill", "experience", "general",
    "industry", "professional", "services", "consulting", "advisory",
    "document", "text", "content", "information", "data", "file",
    "pdf", "upload", "analysis", "review", "risk", "issue", "concern",
    "problem", "error", "warning", "critical", "high", "medium", "low",
    "severity", "category", "location", "quoted", "suggested", "improvement",
    "explanation", "title", "number", "page", "line", "paragraph",
    "company", "corporation", "llc", "inc", "ltd", "limited",
    "address", "street", "city", "state", "zip", "country",
    "email", "phone", "fax", "website", "url",
    "party", "parties", "client", "customer", "vendor", "supplier",
    "contractor", "subcontractor", "agent", "representative",
    "authorized", "signatory", "executive", "officer", "director",
    "board", "shareholder", "stock", "equity", "ownership",
    "revenue", "income", "profit", "loss", "expense", "cost",
    "payment", "fee", "charge", "price", "rate", "discount",
    "invoice", "receipt", "billing", "accounting", "financial",
    "insurance", "policy", "coverage", "premium", "deductible",
    "claim", "settlement", "judgment", "award", "penalty",
    "fine", "sanction", "violation", "infringement", "misuse",
    "unauthorized", "access", "disclosure", "distribution",
    "publication", "reproduction", "derivative", "work",
    "license", "permit", "authorization", "consent", "approval",
    "right", "title", "interest", "claim", "demand", "action",
    "suit", "proceeding", "litigation", "trial", "appeal",
    "court", "judge", "jury", "verdict", "ruling", "order",
    "injunction", "restraining", "protective", "confidentiality",
    "non-disclosure", "nda", "mutual", "unilateral", "one-way",
    "bilateral", "reciprocal", "asymmetric", "symmetric",
    "duration", "term", "period", "interval", "span", "length",
    "expiration", "renewal", "extension", "continuation", "survival",
    "survive", "terminate", "cancel", "revoke", "rescind",
    "rescission", "cancellation", "revocation", "withdrawal",
    "withdraw", "retract", "recall", "revoke", "annul",
    "annulment", "abrogation", "abrogate", "repeal", "repealed",
    "above", "below", "herein", "hereof", "hereto", "hereby",
    "whereas", "therefore", "thereof", "therein", "thereby",
    "pursuant", "accordance", "respect", "regard", "relation",
    "reference", "regarding", "concerning", "pertaining",
    "applicable", "relevant", "pertinent", "material", "substantial",
    "significant", "important", "major", "minor", "trivial",
    "de", "minimis", "materiality", "threshold", "limit",
    "cap", "ceiling", "floor", "maximum", "minimum", "aggregate",
    "total", "partial", "full", "complete", "incomplete",
    "partial", "pro", "rata", "proportionate", "proportional",
    "percentage", "percent", "fraction", "ratio", "portion",
    "share", "allocation", "distribution", "apportionment",
    "division", "separation", "segregation", "isolation",
    "independent", "separate", "distinct", "different", "various",
    "several", "multiple", "numerous", "many", "few", "some",
    "each", "every", "all", "any", "either", "neither", "both",
    "including", "without", "limitation", "example", "instance",
    "such", "same", "similar", "identical", "equivalent",
    "comparable", "corresponding", "matching", "consistent",
    "inconsistent", "contradictory", "conflicting", "opposing",
    "contrary", "reverse", "opposite", "inverse", "reciprocal",
})

LEGAL_KEYWORDS = frozenset({
    "confidential", "liability", "termination", "agreement",
    "indemnification", "indemnify", "breach", "damages",
    "warranty", "compliance", "arbitration", "jurisdiction",
    "obligation", "covenant", "severability", "assignment",
    "governing", "contract", "clause", "provision",
})


@dataclass
class InputQualityResult:
    score: float
    label: str
    is_degraded: bool
    factors: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    DEGRADED_THRESHOLD = 0.35

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_quality_score": round(self.score, 4),
            "input_quality_label": self.label,
            "input_quality_degraded": self.is_degraded,
            "input_quality_factors": self.factors,
            "input_quality_warnings": self.warnings,
        }


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _label_from_score(score: float) -> str:
    if score >= 0.75:
        return "HIGH"
    if score >= 0.45:
        return "MEDIUM"
    return "LOW"


def compute_symbol_density(text: str) -> float:
    """Ratio of non-alphanumeric, non-whitespace characters to total characters.

    High symbol density suggests OCR noise or corrupted text.
    Returns a quality score (1.0 = clean, 0.0 = very noisy).
    """
    if not text:
        return 1.0

    total_chars = len(text)
    symbols = sum(1 for c in text if not c.isalnum() and not c.isspace())
    density = symbols / total_chars

    if density <= 0.08:
        return 1.0
    if density <= 0.15:
        return _clamp(1.0 - (density - 0.08) * 5.0)
    if density <= 0.25:
        return _clamp(0.65 - (density - 0.15) * 3.0)
    if density <= 0.40:
        return _clamp(0.35 - (density - 0.25) * 2.0)
    return _clamp(0.05 - (density - 0.40) * 0.5)


def compute_non_alphanumeric_ratio(text: str) -> float:
    """Ratio of non-alphanumeric characters (including whitespace) to total.

    Returns a quality score. Very high ratios indicate noise.
    """
    if not text:
        return 1.0

    total = len(text)
    alnum = sum(1 for c in text if c.isalnum())
    ratio = 1.0 - (alnum / total)

    if ratio <= 0.25:
        return 1.0
    if ratio <= 0.40:
        return _clamp(1.0 - (ratio - 0.25) * 3.0)
    if ratio <= 0.60:
        return _clamp(0.55 - (ratio - 0.40) * 2.0)
    return _clamp(0.15 - (ratio - 0.60) * 0.5)


def compute_repeated_special_chars(text: str) -> float:
    """Detect repeated special character sequences (e.g., '!!!', '---', '###').

    Returns a quality score. More repeated sequences = lower quality.
    """
    if not text:
        return 1.0

    repeated_pattern = re.compile(r'([^\w\s])\1{2,}')
    matches = repeated_pattern.findall(text)
    count = len(matches)

    total_words = max(1, len(text.split()))
    frequency = count / (total_words / 10.0)

    if frequency <= 0.05:
        return 1.0
    if frequency <= 0.15:
        return _clamp(1.0 - (frequency - 0.05) * 4.0)
    if frequency <= 0.35:
        return _clamp(0.6 - (frequency - 0.15) * 2.0)
    if frequency <= 0.6:
        return _clamp(0.2 - (frequency - 0.35) * 0.6)
    return 0.05


def _count_ocr_substitutions(word: str) -> int:
    """Count common OCR substitution patterns in a word."""
    count = 0
    count += len(re.findall(r'1(?=[a-zA-Z])|(?<=[a-zA-Z])1', word))
    count += len(re.findall(r'0(?=[a-zA-Z])|(?<=[a-zA-Z])0', word))
    count += word.count('@')
    count += word.count('%')
    count += word.count('!')
    count += word.count('$')
    return count


def _has_alternating_pattern(word: str) -> bool:
    """Detect alternating symbol/number/letter patterns like xj29x@@."""
    if len(word) < 4:
        return False
    categories = []
    for c in word:
        if c.isdigit():
            categories.append('d')
        elif c.isalpha():
            categories.append('a')
        elif not c.isspace():
            categories.append('s')
    switches = 0
    for i in range(1, len(categories)):
        if categories[i] != categories[i - 1]:
            switches += 1
    return switches >= 3 and len(word) >= 4


def _has_symbol_burst(word: str) -> bool:
    """Detect repeated symbol clusters within a word."""
    return bool(re.search(r'[!@#$%^&*]{2,}', word))


def _has_excessive_substitutions(word: str) -> bool:
    """Detect words with multiple OCR-style substitutions."""
    return _count_ocr_substitutions(word) >= 2


def compute_malformed_words(text: str) -> tuple[float, int, int]:
    """Detect malformed words that suggest OCR errors.

    Malformed indicators:
    - Words mixing digits and letters abnormally (e.g., 'w0rd', 't3xt', 'TERM1NAT10N')
    - Words with consecutive special characters (e.g., 'wo@@rd', 'CONFIDENTIAL%%%')
    - Words with very high consonant clusters
    - Words containing unusual character combinations
    - Alternating symbol/number/letter patterns
    - Excessive OCR substitutions (1->I, 0->O, @, %, !)
    - Symbol bursts within words

    Returns (quality_score, malformed_count, digit_letter_mix_count).
    """
    if not text:
        return 1.0, 0, 0

    words = text.split()
    if not words:
        return 1.0, 0, 0

    malformed_count = 0
    digit_letter_mix_count = 0
    digit_letter_mix = re.compile(r'(?=.*\d)(?=.*[a-zA-Z])[a-zA-Z0-9]{3,}')
    consecutive_special = re.compile(r'[^\w\s]{2,}')
    long_consonant_cluster = re.compile(r'[bcdfghjklmnpqrstvwxyz]{5,}', re.IGNORECASE)
    unusual_char_mix = re.compile(r'[a-zA-Z][^\w\s][a-zA-Z]')

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
                digit_letter_mix_count += 1

        if consecutive_special.search(word):
            is_malformed = True

        if long_consonant_cluster.search(clean_word):
            is_malformed = True

        if unusual_char_mix.search(word):
            is_malformed = True

        if _has_alternating_pattern(word):
            is_malformed = True

        if _has_excessive_substitutions(word):
            is_malformed = True
            if digit_letter_mix.fullmatch(clean_word):
                digit_letter_mix_count += 1

        if _has_symbol_burst(word):
            is_malformed = True

        if is_malformed:
            malformed_count += 1

    malformed_ratio = malformed_count / len(words)

    if malformed_ratio <= 0.02:
        return 1.0, malformed_count, digit_letter_mix_count
    if malformed_ratio <= 0.06:
        return _clamp(1.0 - (malformed_ratio - 0.02) * 10.0), malformed_count, digit_letter_mix_count
    if malformed_ratio <= 0.15:
        return _clamp(0.6 - (malformed_ratio - 0.06) * 4.0), malformed_count, digit_letter_mix_count
    if malformed_ratio <= 0.30:
        return _clamp(0.24 - (malformed_ratio - 0.15) * 1.5), malformed_count, digit_letter_mix_count
    return 0.01, malformed_count, digit_letter_mix_count


def compute_dictionary_word_ratio(text: str) -> float:
    """Ratio of words that match common English/legal dictionary entries.

    Low dictionary-word ratio suggests OCR noise or corrupted input.
    Returns a quality score.
    """
    if not text:
        return 1.0

    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    if not words:
        return 0.3

    recognized = sum(1 for w in words if w in COMMON_ENGLISH_WORDS)
    ratio = recognized / len(words)

    if ratio >= 0.40:
        return 1.0
    if ratio >= 0.25:
        return _clamp(0.6 + (ratio - 0.25) * 2.67)
    if ratio >= 0.10:
        return _clamp(0.2 + (ratio - 0.10) * 2.67)
    return _clamp(ratio * 2.0)


def compute_uppercase_ratio(text: str) -> float:
    """Compute the ratio of uppercase letters to total letters.

    Very high uppercase ratios suggest OCR corruption or shouting.
    Returns a quality score (1.0 = normal, 0.0 = all caps).
    """
    if not text:
        return 1.0

    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 1.0

    uppercase_count = sum(1 for c in letters if c.isupper())
    ratio = uppercase_count / len(letters)

    if ratio <= 0.50:
        return 1.0
    if ratio <= 0.70:
        return _clamp(1.0 - (ratio - 0.50) * 2.5)
    if ratio <= 0.85:
        return _clamp(0.5 - (ratio - 0.70) * 2.5)
    if ratio <= 0.95:
        return _clamp(0.12 - (ratio - 0.85) * 1.0)
    return 0.02


def compute_vowel_ratio(text: str) -> float:
    """Compute the ratio of vowels to total alphabetic characters.

    Very low vowel ratios suggest corrupted or non-text content.
    Returns a quality score (1.0 = normal, 0.0 = no vowels).
    """
    if not text:
        return 1.0

    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 1.0

    vowels = sum(1 for c in letters if c.lower() in 'aeiou')
    ratio = vowels / len(letters)

    if ratio >= 0.30:
        return 1.0
    if ratio >= 0.20:
        return _clamp(0.5 + (ratio - 0.20) * 5.0)
    if ratio >= 0.10:
        return _clamp(0.1 + (ratio - 0.10) * 4.0)
    return _clamp(ratio * 1.0)


def compute_symbol_burst_density(text: str) -> float:
    """Detect clusters of 3+ consecutive symbols (e.g., %%%, &&&, ###).

    Returns a quality score. More bursts = lower quality.
    """
    if not text:
        return 1.0

    burst_pattern = re.compile(r'[!@#$%^&*+=~|\\<>?]{3,}')
    bursts = burst_pattern.findall(text)
    burst_count = len(bursts)

    total_words = max(1, len(text.split()))
    burst_ratio = burst_count / (total_words / 5.0)

    if burst_ratio <= 0.05:
        return 1.0
    if burst_ratio <= 0.2:
        return _clamp(1.0 - (burst_ratio - 0.05) * 4.0)
    if burst_ratio <= 0.5:
        return _clamp(0.4 - (burst_ratio - 0.2) * 1.0)
    return 0.05


def compute_keyword_trust(text: str, malformed_ratio: float, symbol_density_score: float) -> float:
    """Assess whether legal keywords in text are trustworthy.

    Legal keywords alone should NOT increase quality if:
    - malformed ratio is high
    - symbol density is high

    Returns a quality score.
    """
    if not text:
        return 1.0

    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    if not words:
        return 0.5

    legal_matches = sum(1 for w in words if w in LEGAL_KEYWORDS)
    legal_ratio = legal_matches / len(words)

    if legal_ratio < 0.05:
        return 1.0

    if malformed_ratio > 0.15 or symbol_density_score < 0.3:
        return _clamp(0.35 - legal_ratio * 0.5)

    if malformed_ratio > 0.05 or symbol_density_score < 0.5:
        return _clamp(0.6 - legal_ratio * 0.3)

    return 1.0


QUALITY_WEIGHTS = {
    "symbol_density": 0.15,
    "non_alphanumeric_ratio": 0.10,
    "repeated_special_chars": 0.12,
    "malformed_words": 0.20,
    "dictionary_word_ratio": 0.13,
    "uppercase_ratio": 0.10,
    "vowel_ratio": 0.08,
    "symbol_burst_density": 0.07,
    "keyword_trust": 0.05,
}

MALFORMED_HARD_DEGRADE_THRESHOLD = 0.15
SYMBOL_DENSITY_HARD_DEGRADE_THRESHOLD = 0.30
SYMBOL_BURST_HARD_DEGRADE_THRESHOLD = 0.3
DIGIT_LETTER_MIX_HARD_DEGRADE_COUNT = 2
REPEATED_SPECIAL_HARD_DEGRADE_THRESHOLD = 0.35


def assess_input_quality(text: str) -> InputQualityResult:
    """Assess the quality of input text using multiple heuristics.

    Returns an InputQualityResult with score, label, and any warnings.
    """
    if not text or not text.strip():
        return InputQualityResult(
            score=0.0,
            label="LOW",
            is_degraded=True,
            factors={},
            warnings=["Input text is empty or whitespace-only"],
        )

    factors: Dict[str, float] = {}
    warnings: List[str] = []

    malformed_score, malformed_count, digit_letter_mix_count = compute_malformed_words(text)
    total_words = max(1, len(text.split()))
    malformed_ratio = malformed_count / total_words

    factors["symbol_density"] = compute_symbol_density(text)
    factors["non_alphanumeric_ratio"] = compute_non_alphanumeric_ratio(text)
    factors["repeated_special_chars"] = compute_repeated_special_chars(text)
    factors["malformed_words"] = malformed_score
    factors["dictionary_word_ratio"] = compute_dictionary_word_ratio(text)
    factors["uppercase_ratio"] = compute_uppercase_ratio(text)
    factors["vowel_ratio"] = compute_vowel_ratio(text)
    factors["symbol_burst_density"] = compute_symbol_burst_density(text)
    factors["keyword_trust"] = compute_keyword_trust(
        text, malformed_ratio, factors["symbol_density"]
    )

    weighted = sum(factors[k] * QUALITY_WEIGHTS[k] for k in QUALITY_WEIGHTS)
    score = _clamp(weighted)

    hard_degrade_triggered = False

    if malformed_ratio > MALFORMED_HARD_DEGRADE_THRESHOLD:
        hard_degrade_triggered = True
        logger.warning(
            "[InputQuality] HARD_DEGRADE_TRIGGERED: malformed_ratio=%.2f > threshold=%.2f",
            malformed_ratio, MALFORMED_HARD_DEGRADE_THRESHOLD
        )
    if factors["symbol_density"] < SYMBOL_DENSITY_HARD_DEGRADE_THRESHOLD:
        hard_degrade_triggered = True
        logger.warning(
            "[InputQuality] HARD_DEGRADE_TRIGGERED: symbol_density=%.2f < threshold=%.2f",
            factors["symbol_density"], SYMBOL_DENSITY_HARD_DEGRADE_THRESHOLD
        )
    if factors["symbol_burst_density"] < SYMBOL_BURST_HARD_DEGRADE_THRESHOLD:
        hard_degrade_triggered = True
        logger.warning(
            "[InputQuality] HARD_DEGRADE_TRIGGERED: symbol_burst_density=%.2f < threshold=%.2f",
            factors["symbol_burst_density"], SYMBOL_BURST_HARD_DEGRADE_THRESHOLD
        )
    if digit_letter_mix_count >= DIGIT_LETTER_MIX_HARD_DEGRADE_COUNT:
        hard_degrade_triggered = True
        logger.warning(
            "[InputQuality] HARD_DEGRADE_TRIGGERED: digit_letter_mix_count=%d >= threshold=%d",
            digit_letter_mix_count, DIGIT_LETTER_MIX_HARD_DEGRADE_COUNT
        )
    if factors["repeated_special_chars"] < REPEATED_SPECIAL_HARD_DEGRADE_THRESHOLD:
        hard_degrade_triggered = True
        logger.warning(
            "[InputQuality] HARD_DEGRADE_TRIGGERED: repeated_special_chars=%.2f < threshold=%.2f",
            factors["repeated_special_chars"], REPEATED_SPECIAL_HARD_DEGRADE_THRESHOLD
        )

    if hard_degrade_triggered:
        score = min(score, 0.20)
        logger.warning("[InputQuality] HARD_DEGRADE_TRIGGERED: score capped to %.2f", score)

    label = _label_from_score(score)
    is_degraded = score < InputQualityResult.DEGRADED_THRESHOLD

    logger.info(
        "[InputQuality] malformed_ratio=%.2f symbol_density=%.2f uppercase_ratio=%.2f digit_letter_mix_count=%d",
        malformed_ratio, factors["symbol_density"], factors["uppercase_ratio"], digit_letter_mix_count
    )

    if factors["symbol_density"] < 0.5:
        warnings.append("High symbol density detected - possible OCR noise")
    if factors["non_alphanumeric_ratio"] < 0.5:
        warnings.append("High non-alphanumeric character ratio")
    if factors["repeated_special_chars"] < 0.5:
        warnings.append("Repeated special character sequences detected")
    if factors["malformed_words"] < 0.5:
        warnings.append("Significant number of malformed words detected")
    if factors["dictionary_word_ratio"] < 0.5:
        warnings.append("Low dictionary-word ratio - text may be corrupted")
    if factors["uppercase_ratio"] < 0.5:
        warnings.append("High uppercase ratio - possible OCR corruption")
    if factors["vowel_ratio"] < 0.5:
        warnings.append("Low vowel ratio - text may be corrupted or non-linguistic")
    if factors["symbol_burst_density"] < 0.5:
        warnings.append("Symbol burst clusters detected - possible OCR noise")
    if factors["keyword_trust"] < 0.5:
        warnings.append("Legal keywords present but text quality too low for trust")

    if is_degraded:
        logger.warning(
            "[InputQuality] Input quality DEGRADED: score=%.2f label=%s factors=%s",
            score, label, {k: round(v, 3) for k, v in factors.items()}
        )
    else:
        logger.info(
            "[InputQuality] Input quality OK: score=%.2f label=%s",
            score, label
        )

    return InputQualityResult(
        score=score,
        label=label,
        is_degraded=is_degraded,
        factors=factors,
        warnings=warnings,
    )
