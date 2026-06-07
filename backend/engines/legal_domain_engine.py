"""
Legal Domain Detection Engine

Detects whether input text belongs to the legal/contract domain
and suppresses hallucinated legal analysis for non-legal content.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set
from enum import Enum

from backend.logger import logger


class DocumentDomain(str, Enum):
    LEGAL = "LEGAL"
    POSSIBLY_LEGAL = "POSSIBLY_LEGAL"
    NON_LEGAL = "NON_LEGAL"


@dataclass
class DomainDetectionResult:
    domain: DocumentDomain
    confidence: float
    legal_keyword_ratio: float
    structure_score: float
    legal_phrase_density: float
    non_legal_penalty: float
    factors: Dict[str, float] = field(default_factory=dict)


NON_LEGAL_THRESHOLD = 0.08
POSSIBLY_LEGAL_THRESHOLD = 0.20

# Single-word legal keywords (checked via word tokenization)
LEGAL_KEYWORDS: Set[str] = {
    "agreement", "party", "parties", "confidential", "termination",
    "liability", "indemnify", "indemnification", "indemnity",
    "indemnified", "indemnifies", "indemnitor", "indemnitee",
    "clause", "recipient", "discloser", "warranty", "warranties",
    "obligation", "obligations", "obligated",
    "breach", "breached", "breaches",
    "damages", "arbitration", "arbitrate", "arbitral",
    "jurisdiction", "severability", "severable",
    "assignment", "assignable", "assigns",
    "covenant", "covenants",
    "provision", "provisions",
    "hereby", "whereas", "thereof", "therein", "herein",
    "hereto", "hereunder", "thereunder", "thereto",
    "pursuant", "notwithstanding",
    "representation", "representations",
    "compliance", "compliant",
    "enforceable", "unenforceable", "enforceability",
    "void", "null", "voidable",
    "mutual", "unilateral", "bilateral",
    "executed", "execution", "execute",
    "counterparts", "counterpart",
    "waiver", "waive", "waived", "waives",
    "amendment", "amend", "amended", "amends",
    "modification", "modify", "modified",
    "venue", "forum",
    "mediation", "mediate", "mediator",
    "expiration", "expire", "expired", "expires",
    "renewal", "renew", "renewed", "renews",
    "signature", "signatory", "signatories",
    "definitions", "interpretation",
    "remedies", "remedy",
    "defend", "defended", "defends",
    "governing", "survive", "survives", "survived",
    "disclosing", "receiving",
    "residuals", "residual",
    "successors", "successor",
    "license", "licensor", "licensee", "licensing",
    "warrants", "warranted", "warranting",
    "covenants", "covenanted",
    "indemnification", "indemnify",
    "confidentiality", "confidentially",
    "terminate", "terminates", "terminated", "terminating",
    "liable", "liabilities",
    "stipulate", "stipulation", "stipulated",
    "adjudication", "adjudicate", "adjudicated",
    "award", "awarded", "awards",
    "binding", "binds",
    "consent", "consented", "consents",
    "deem", "deemed", "deems",
    "dispute", "disputes", "disputed",
    "entitled", "entitle",
    "estoppel", "waiver",
    "indemnification", "indemnify",
    "injunctive", "injunction",
    "irreparable", "irreparably",
    "material", "materially", "materiality",
    "negligence", "negligent",
    "obligor", "obligee",
    "prejudice", "prejudiced",
    "proceed", "proceeding", "proceedings",
    "ratify", "ratification", "ratified",
    "reimburse", "reimbursement", "reimbursed",
    "relief", "relieved",
    "rescind", "rescission", "rescinded",
    "revoke", "revocation", "revoked",
    "sanction", "sanctions", "sanctioned",
    "settle", "settlement", "settled",
    "sue", "sued", "sues", "suing",
    "tender", "tendered",
    "termination", "terminate",
    "title", "titled",
    "tort", "torts",
    "trustee", "trust",
    "underwrite", "underwriting", "underwritten",
    "void", "voidable",
    "witness", "witnesseth",
    "royalty", "royalties",
    "affiliate", "affiliates", "affiliated",
    "subsidiary", "subsidiaries",
    "certify", "certification", "certified",
    "indemnity", "indemnities",
    "defend", "defendant",
    "plaintiff", "plaintiffs",
    "litigation", "litigate", "litigant",
    "appeal", "appellate", "appellant",
    "testimony", "testify", "deposition",
    "subpoena", "subpoenas",
    "arbitrator", "arbitrators",
    "mediator", "mediators",
    "notary", "notarize", "notarized",
    "affidavit", "affidavits",
    "exhibit", "exhibits",
    "schedule", "schedules", "scheduled",
    "appendix", "appendices",
    "annex", "annexes",
    "recital", "recitals",
    "preamble", "preambles",
    "operative", "operatives",
    "conclusive", "conclusively",
    "discretion", "discretionary",
    "sole", "solely",
    "exclusive", "exclusively",
    "cumulative", "cumulatively",
    "consecutive", "consecutively",
    "successive", "successively",
    "retroactive", "retroactively",
    "prospective", "prospectively",
    "prorated", "prorate", "proration",
    "abatement", "abate",
    "accrual", "accrue", "accrued",
    "aggregate", "aggregated",
    "allocable", "allocate", "allocation",
    "apportion", "apportionment",
    "attributable", "attribute",
    "chargeable", "charge",
    "deductible", "deduct",
    "allowable", "allowance",
    "forfeit", "forfeiture",
    "liquidated", "liquidation",
    "mitigate", "mitigation",
    "subrogate", "subrogation",
    "contribution", "contribute",
    "apportionment", "apportion",
    "discharge", "discharged",
    "fulfill", "fulfillment",
    "perform", "performance", "performed",
    "satisfy", "satisfaction", "satisfied",
    "comply", "complying", "complied",
    "observe", "observed", "observes",
    "keep", "keeping",
    "maintain", "maintained", "maintains",
    "preserve", "preserved", "preserves",
    "protect", "protects", "protected",
    "safeguard", "safeguarded",
    "restrict", "restricts", "restricted", "restriction",
    "limit", "limits", "limited", "limitation",
    "prohibit", "prohibits", "prohibited", "prohibition",
    "exclude", "excludes", "excluded", "exclusion",
    "include", "includes", "included", "inclusion",
    "comprise", "comprises", "comprised",
    "consist", "consists", "consisted",
    "contain", "contains", "contained",
    "set", "sets",
    "specify", "specifies", "specified", "specification",
    "define", "defines", "defined", "defining",
    "mean", "means", "meaning",
    "refer", "refers", "referred", "referring",
    "describe", "describes", "described",
    "designate", "designates", "designated",
    "identify", "identifies", "identified",
    "purpose", "purposes",
    "intend", "intends", "intended", "intention",
    "contemplate", "contemplates", "contemplated",
    # Extended legal/business keywords for broader contract coverage
    "contract", "contracts", "contractual",
    "services", "service",
    "provider", "providers",
    "deliverable", "deliverables",
    "intellectual",
    "payment", "payments", "payable",
    "fee", "fees",
    "cost", "costs", "costing",
    "invoice", "invoices",
    "project", "projects",
    "scope",
    "acceptance", "accept",
    "approval", "approve", "approved",
    "data",
    "privacy",
    "security",
    "software",
    "technology", "technologies",
    "professional",
    "consulting", "consultant", "consultants",
    "vendor", "vendors",
    "supplier", "suppliers",
    "customer", "customers",
    "client", "clients",
    "grant", "grants",
    "sponsor", "sponsors", "sponsored", "sponsorship",
    "research",
    "collaboration", "collaborate",
    "subcontract", "subcontractor", "subcontractors",
    "teaming",
    "procurement", "procure",
    "solicitation", "solicit",
    "respondent", "respondents",
    "proposal", "proposals",
    "bid", "bids", "bidding",
    "tender", "tenders",
    "quote", "quotes", "quotation",
    "rates", "rate",
    "hourly", "monthly", "annual", "quarterly",
    "retainer", "retainers",
    "reimbursement", "reimburse", "reimbursable",
    "audit", "audits", "auditing",
    "inspection", "inspect",
    "certification", "certify", "certified",
    "insurance", "insure", "insured",
    "indemnitor", "indemnitee",
    "prevail", "prevailing",
    "substantial", "substantially",
    "materiality", "material",
    "knowledge",
    "belief", "believe",
    "aware", "awareness",
    "notify", "notification", "notified", "notifies",
    "approve", "approval", "approved",
    "authorize", "authorization", "authorized", "authorizes",
    "consent", "consents", "consented",
    "waiver", "waive", "waived", "waives",
    "release", "releases", "released",
    "discharge", "discharged",
    "satisfy", "satisfaction", "satisfied",
    "fulfill", "fulfilled", "fulfillment",
    "complete", "completes", "completed", "completion",
}

# Multi-word legal phrases for density calculation
LEGAL_PHRASES: Set[str] = {
    "governing law", "survive termination", "hold harmless",
    "force majeure", "dispute resolution", "confidential information",
    "disclosing party", "receiving party", "effective date",
    "binding effect", "entire agreement", "integration clause",
    "severability clause", "choice of law", "binding arbitration",
    "confidentiality obligation", "survival clause",
    "notice provision", "indemnification obligation", "liability cap",
    "limitation of liability", "cap on liability",
    "confidentiality agreement", "non-disclosure agreement",
    "service agreement", "license agreement", "master agreement",
    "representations and warranties", "conditions precedent",
    "events of default", "specific performance",
    "injunctive relief", "attorneys fees", "legal fees",
    "indemnify and hold harmless", "aggregate liability",
    "consequential damages", "incidental damages",
    "direct damages", "indirect damages", "punitive damages",
    "limitation period", "statute of limitations",
    "trade secret", "proprietary information",
    "residual knowledge", "compelled disclosure",
    "required disclosure", "court order",
    "upon termination", "after termination",
    "irreparable harm", "irreparable injury",
    "adequate remedy", "including but not limited to",
    "including without limitation", "notwithstanding the foregoing",
    "subject to the terms", "pursuant to",
    "in accordance with", "as set forth",
    "defined in", "referred to as",
    "hereinafter", "aforesaid",
    "party hereto", "party thereto",
    "parties hereto", "parties thereto",
    "this agreement", "this contract",
    "the agreement", "the contract",
    "confidential treatment", "mutual confidentiality",
    "unilateral confidentiality", "mutual non-disclosure",
    "non-disclosure obligations", "confidentiality obligations",
    "survival of obligations", "survival period",
    "return of materials", "return or destroy",
    "no license", "no right",
    "remedies upon breach", "default remedies",
    "governing law and jurisdiction", "venue and jurisdiction",
    "waiver of jury trial", "jury waiver",
    "class action waiver", "class action",
    "prevailing party", "substantially prevailing",
    "costs and expenses", "expenses incurred",
    "reasonable attorneys", "outside counsel",
    "independent counsel", "legal representation",
    "authorized representative", "duly authorized",
    "executed this", "signed this",
    "in witness whereof", "witness whereof",
    "duly executed", "properly executed",
    "binding and enforceable", "valid and binding",
    "full force and effect", "force and effect",
    "terms and conditions", "terms hereof",
    "provisions hereof", "sections hereof",
    "clauses hereof", "paragraphs hereof",
    "further assurance", "further assurances",
    "further guarantees", "further guaranties",
    "no oral modification", "no oral amendment",
    "written modification", "written amendment",
    "entire understanding", "complete agreement",
    "supersedes all prior", "supersedes any",
    "merger clause", "integration provision",
    "counterpart", "facsimile signature",
    "electronic signature", "digital signature",
    "shall be governed", "shall be construed",
    "shall be interpreted", "shall be resolved",
    "shall be settled", "shall be decided",
    "herein contained", "herein set forth",
    "therein contained", "therein set forth",
    "by and between", "among and between",
    # Extended contract/business phrases for broader coverage
    "service provider", "services provider",
    "scope of work", "statement of work",
    "intellectual property", "intellectual property rights",
    "third party", "third-party", "third parties",
    "work product", "work for hire",
    "payment terms", "payment schedule",
    "fee schedule", "fee structure",
    "professional services", "consulting services",
    "mutual agreement", "mutual consent",
    "written notice", "prior written notice",
    "prior written consent", "written consent",
    "reasonable efforts", "commercially reasonable efforts",
    "best efforts", "reasonable endeavours",
    "data protection", "data privacy",
    "personal data", "personal information",
    "confidential treatment", "confidential information",
    "security breach", "data breach",
    "acceptance criteria", "acceptance testing",
    "delivery schedule", "delivery timeline",
    "project plan", "project schedule",
    "key personnel", "key staff",
    "change order", "change request",
    "statement of work", "scope of services",
    "service level", "service levels",
    "service level agreement", "service level objective",
    "standard of care", "standard of work",
    "warranty period", "warranty term",
    "defect remedy", "remedy period",
    "error correction", "bug fix",
    "maintenance and support", "support and maintenance",
    "transition assistance", "transition services",
    "termination for convenience", "termination for cause",
    "termination for breach", "termination upon breach",
    "expiration of the term", "end of the term",
    "renewal term", "renewal period", "automatic renewal",
    "initial term", "initial period",
    "notice period", "notice of termination",
    "cure period", "grace period",
    "governing law and jurisdiction", "governing law and venue",
    "exclusive jurisdiction", "non-exclusive jurisdiction",
    "waiver of jury", "jury trial waiver",
    "class action", "class action waiver",
    "attorney fees", "attorneys' fees",
    "legal fees", "court costs",
    "costs and expenses", "expenses and costs",
    "prevailing party", "substantially prevailing party",
}

# Patterns that indicate contract structure
CONTRACT_STRUCTURE_PATTERNS = [
    re.compile(r"(?im)^\s*(?:this\s+)?(?:confidentiality|non.?disclosure|mutual|unilateral|bilateral|service|license|master|employment|consulting|consultancy|settlement|purchase|supply|distributor|franchise|joint venture|partnership|shareholder|subscription|membership|software|development|professional services|outsourcing|sponsorship|sponsored|marketing|advertising|agency|broker|management|advisory|loan|credit|finance|leasing|rental|warranty|guaranty|indemnity|escrow|custody|clearing|settlement|collateral|security|pledge|hypothecation|research|collaboration|grant|material transfer|teaming|subcontract|subcontracting|procurement|consultant|vendor|supplier|fabrication|manufacturing|technology transfer|clinical trial|clinical|testing|evaluation|feasibility|studies|funding|endowment|fellowship|scholarship|internship|trainee|apprenticeship|exchange|secondment|assignment)\s+(?:agreement|contract|understanding|instrument|deed|letter|arrangement|terms)\b"),
    re.compile(r"(?im)^\s*\d+\.\s+[A-Z]"),
    re.compile(r"(?im)^\s*(?:article|section|clause|paragraph|schedule|exhibit|appendix|annex)\s+\d+"),
    re.compile(r"(?im)^\s*whereas\b"),
    re.compile(r"(?im)(?:this\s+)?agreement\s+is\s+(?:entered\s+into|made|executed)\s+(?:as\s+of|on\s+this)\b"),
    re.compile(r"(?im)by\s+and\s+between\b"),
    re.compile(r"(?im)hereinafter\s+(?:referred\s+to\s+as|called)\b"),
    re.compile(r"(?im)(?:effective|execution|commencement)\s+date\b"),
    re.compile(r"(?im)(?:duly\s+)?authorized\s+(?:representative|officer|signatory|signatories)\b"),
    re.compile(r"(?im)intending\s+to\s+be\s+legally\s+bound\b"),
    re.compile(r"(?im)(?:signature|signed|executed|countersigned)\s+(?:below|above|hereto|hereunder|on|this)\b"),
    re.compile(r"(?im)(?:party|parties)\s+(?:hereto|thereto|hereunder|thereunder)\b"),
    re.compile(r'(?im)"[A-Z][A-Z\s]+"\s+(?:means|shall\s+mean|refers\s+to)\b'),
    re.compile(r"(?im)(?:confidential\s+information|proprietary\s+information)\s+(?:means|shall\s+mean|includes?)\b"),
    re.compile(r"(?im)^\s*IN\s+(?:WITNESS|WITNESSETH)\b"),
    re.compile(r"(?im)^\s*NOW\s+(?:THEREFORE|IT\s+IS\s+HEREBY)\b"),
    re.compile(r"(?im)\b(?:hereby\s+agrees?|hereby\s+covenants?|hereby\s+represents?|hereby\s+warrants?)\b"),
    re.compile(r"(?im)\b(?:shall\s+(?:mean|include|not\s+exceed|be\s+(?:construed|interpreted|governed|binding|effective|deemed)))\b"),
    re.compile(r"(?im)\b(?:notwithstanding\s+(?:the\s+)?(?:foregoing|anything|any\s+provision))\b"),
    re.compile(r"(?im)(?:survive|survives)\s+(?:termination|cancellation|expiration)\b"),
    re.compile(r"(?im)(?:indemnify|indemnification)\s+(?:against|for|from|with\s+respect\s+to)\b"),
    re.compile(r"(?im)\b(?:without\s+(?:limiting|limitation|prejudice|recourse|notice|cause|fault))\b"),
    re.compile(r"(?im)(?:defined\s+(?:terms?|words?|expressions?)|capitalized\s+terms?)\b"),
    re.compile(r"(?im)(?:terms?\s+(?:and\s+conditions?|hereof|thereof|of\s+(?:this|the)\s+(?:agreement|contract)))\b"),
    re.compile(r"(?im)(?:this\s+(?:agreement|contract|instrument|document|deed|instrument))\s+(?:sets?\s+forth|governs?|establishes?|defines?)\b"),
    re.compile(r"(?im)\b(?:IN|UNDER|PURSUANT\s+TO)\s+THIS\s+(?:AGREEMENT|CONTRACT)\b"),
]

# Non-legal text patterns (penalized)
NON_LEGAL_PATTERNS_STRONG = [
    re.compile(r"(?i)\b(?:cup[s]?\s+of\s+|cup[s]?\s+(?:all-purpose|granulated|packed)|tablespoon[s]?|teaspoon[s]?|preheat|preheated|bake|baked|baking|oven\s+\d+|ingredients?|mix\s+(?:together|well|until|in|the|thoroughly)|stir\s+in|beat\s+(?:until|together|in)|baking\s+(?:sheet|soda|powder|dish|pan)|chopped|melted|recipe\s+(?:calls|makes|yields|is|for))\b"),
    re.compile(r"(?i)\b(?:once\s+upon\s+a\s+time|chapter\s+\d+|the\s+end\.|\"i\s+(?:said|told|asked|thought|murmured|whispered|shouted|cried|laughed)\"|he\s+(?:whispered|shouted|cried|laughed|murmured)\b|she\s+(?:whispered|shouted|cried|laughed|murmured)\b)"),
    re.compile(r"(?i)\b(?:in\s+my\s+opinion|i\s+think\s+|i\s+believe\s+|i\s+feel\s+|i\s+guess\s+|i\s+suppose\s+|i\s+personally\s+)"),
    re.compile(r"(?i)\b(?:touchdown|quarterback|inning|pitcher|home\s+run|goalkeeper|penalty\s+(?:kick|shot)|free\s+throw|three.?pointer|offside|offensive|defensive\s+(?:lineman|back|tackle|end))\b"),
    re.compile(r"(?i)\b(?:ingredients[:;]|instructions[:;]|directions[:;]|steps[:;]|method[:;]|procedure[:;])\s*$", re.MULTILINE),
    re.compile(r"(?i)^\s*<!--.*?-->\s*$", re.MULTILINE),
]

NON_LEGAL_PATTERNS_WEAK = [
    re.compile(r"(?i)\bi\s+(?:was|were|have|had|will|would|could|should|love|hate|like|really|just|want|need|hope|wish|remember|recall|miss|enjoy|adore|dislike)\b"),
    re.compile(r"(?i)\byou\s+(?:are|were|have|had|will|would|could|should|can|need|want|love|hate|like|really|just|think|know|should|must|might)\b"),
    re.compile(r"(?i)\b(?:oh\s+(?:wow|yes|no|my|dear)|well,\s+(?:i|it|that)|so,\s+(?:i|we|you|they)|anyway|anyways)\b"),
    re.compile(r"(?i)\b(?:lol|lmao|rofl|omg|wtf|idk|tbh|imo|imho)\b"),
    re.compile(r"(?i)\?{2,}|!{3,}"),
    re.compile(r"(?i)\b(?:story|storytelling|narrative|novel|fiction|fictional|character|plot|chapter|page\s+\d+)\b"),
    re.compile(r"(?i)\b(?:my\s+(?:favorite|favourite|best|worst|first|last|next|recent|new|old|family|personal|own))\b"),
    re.compile(r"(?i)\b(?:let\s+me\s+(?:tell|share|start|begin|introduce|explain))\b"),
]

DOMAIN_SUPPRESSION_MESSAGE = "Document does not appear to be a legal contract or agreement."


def compute_legal_keyword_ratio(text: str) -> float:
    """Compute the ratio of legal keywords to total words in the text."""
    if not text or not text.strip():
        return 0.0

    words = _get_words(text)
    if not words:
        return 0.0

    legal_count = sum(1 for w in words if w in LEGAL_KEYWORDS)
    total = len(words)

    return legal_count / total


def compute_contract_structure_score(text: str) -> float:
    """Score how strongly the text resembles a legal contract structure."""
    if not text or not text.strip():
        return 0.0

    matches = sum(1 for pattern in CONTRACT_STRUCTURE_PATTERNS if pattern.search(text))
    max_possible = len(CONTRACT_STRUCTURE_PATTERNS)

    raw_score = matches / max_possible

    if matches >= 3:
        raw_score = min(1.0, raw_score * 1.3)
    if matches >= 6:
        raw_score = min(1.0, raw_score * 1.2)

    return raw_score


def compute_legal_phrase_density(text: str) -> float:
    """Compute the density of multi-word legal phrases in the text."""
    if not text or not text.strip():
        return 0.0

    words = text.split()
    if not words:
        return 0.0

    text_lower = text.lower()
    phrase_matches = 0
    for phrase in LEGAL_PHRASES:
        count = len(re.findall(re.escape(phrase), text_lower))
        phrase_matches += count

    total_words = len(words)
    return phrase_matches / total_words


def compute_non_legal_penalty(text: str) -> float:
    """Compute a penalty score for non-legal text patterns.

    Returns 0.0 for clearly legal, higher values for clearly non-legal.
    """
    if not text or not text.strip():
        return 0.5

    strong_matches = sum(1 for pattern in NON_LEGAL_PATTERNS_STRONG if pattern.search(text))
    weak_matches = sum(1 for pattern in NON_LEGAL_PATTERNS_WEAK if pattern.search(text))

    penalty = (strong_matches * 0.20) + (weak_matches * 0.08)

    return min(1.0, penalty)


def _get_words(text: str) -> List[str]:
    """Extract lowercase words of length >= 3 from text."""
    return re.findall(r"[a-zA-Z]{3,}", text.lower())


def compute_document_domain_confidence(text: str) -> DomainDetectionResult:
    """Compute the domain classification of the input text.

    Returns:
        DomainDetectionResult with domain, confidence, and factor scores.
    """
    legal_keyword_ratio = compute_legal_keyword_ratio(text)
    structure_score = compute_contract_structure_score(text)
    legal_phrase_density = compute_legal_phrase_density(text)
    non_legal_penalty = compute_non_legal_penalty(text)

    legal_signal = (
        legal_keyword_ratio * 0.40 +
        structure_score * 0.35 +
        legal_phrase_density * 0.25
    )

    effective_score = max(0.0, legal_signal - non_legal_penalty)

    # Boost for employment agreements: the title pattern alone may not push
    # the blended score past LEGAL threshold, but employment agreements are
    # unequivocally legal documents.
    if re.search(r"(?im)^\s*EMPLOYMENT\s+(?:AGREEMENT|CONTRACT)\b", text):
        effective_score = max(effective_score, POSSIBLY_LEGAL_THRESHOLD + 0.05)

    if effective_score <= NON_LEGAL_THRESHOLD:
        domain = DocumentDomain.NON_LEGAL
    elif effective_score < POSSIBLY_LEGAL_THRESHOLD:
        domain = DocumentDomain.POSSIBLY_LEGAL
    else:
        domain = DocumentDomain.LEGAL

    suppression_triggered = domain == DocumentDomain.NON_LEGAL

    logger.info("[DomainDetection] domain=%s effective_score=%.4f "
                "legal_keyword_ratio=%.4f structure_score=%.4f "
                "legal_phrase_density=%.4f non_legal_penalty=%.4f "
                "legal_signal=%.4f suppression_triggered=%s input_length=%d",
                domain.value, effective_score,
                legal_keyword_ratio, structure_score,
                legal_phrase_density, non_legal_penalty,
                legal_signal, suppression_triggered, len(text))

    return DomainDetectionResult(
        domain=domain,
        confidence=effective_score,
        legal_keyword_ratio=legal_keyword_ratio,
        structure_score=structure_score,
        legal_phrase_density=legal_phrase_density,
        non_legal_penalty=non_legal_penalty,
        factors={
            "legal_keyword_ratio": round(legal_keyword_ratio, 4),
            "structure_score": round(structure_score, 4),
            "legal_phrase_density": round(legal_phrase_density, 4),
            "non_legal_penalty": round(non_legal_penalty, 4),
            "legal_signal": round(legal_signal, 4),
            "effective_score": round(effective_score, 4),
        },
    )
