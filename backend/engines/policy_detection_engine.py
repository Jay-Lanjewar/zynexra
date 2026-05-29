"""
Policy/Procedure Document Detection Engine

Detects whether input text is a policy or procedure document
(administrative rules, eligibility criteria, guidelines, rebate policies,
hostel regulations, academic policies, institutional notices, etc.)
rather than a contractual agreement.

Returns a NON_CONTRACT_POLICY result for policy documents that lack
contractual signals, diverting them from the legal-risk audit pipeline.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set
from enum import Enum

from backend.logger import logger


class PolicyDetection(str, Enum):
    POLICY = "POLICY"
    NOT_POLICY = "NOT_POLICY"
    UNCLEAR = "UNCLEAR"


@dataclass
class PolicyDetectionResult:
    detection: PolicyDetection
    confidence: float
    policy_keyword_score: float
    contractual_signal_score: float
    policy_type: str
    matched_policy_keywords: List[str]
    matched_contractual_signals: List[str]
    explanation: str
    factors: Dict[str, float] = field(default_factory=dict)


POLICY_KEYWORD_THRESHOLD = 0.04
CONTRACTUAL_SIGNAL_THRESHOLD = 0.015
POLICY_DOMINANCE_RATIO = 2.5

POLICY_KEYWORDS: Set[str] = {
    "policy", "policies",
    "procedure", "procedures", "procedural",
    "guideline", "guidelines",
    "eligibility", "eligible", "ineligible",
    "criteria", "criterion",
    "regulation", "regulations", "regulatory",
    "rule", "rules",
    "handbook", "manual",
    "protocol", "protocols",
    "directive", "directives",
    "framework",
    "ordinance", "ordinances",
    "bylaw", "bylaws", "by-law", "by-laws",
    "statute", "statutes", "statutory",
    "code of conduct",
    "standard operating procedure", "sop",
    "compliance", "compliant",
    "administrative", "administration",
    "rebate", "rebates",
    "hostel", "accommodation",
    "academic", "curricular", "curriculum",
    "syllabus", "syllabi",
    "enrollment", "enrolment", "enroll", "enrol",
    "admission", "admissions", "admit",
    "scholarship", "scholarships",
    "fellowship", "fellowships",
    "tuition",
    "refund", "refunds", "refundable",
    "disciplinary", "grievance",
    "appeal", "appeals",
    "ethics", "ethical", "unethical",
    "whistleblower", "whistleblowing",
    "notification", "notifications", "notify",
    "notice", "notices",
    "institutional",
    "mandatory", "compulsory",
    "expulsion", "suspend", "suspension",
    "probation", "probationary",
    "sanction", "sanctions",
    "violation", "violations",
    "offence", "offense", "offences", "offenses",
    "misconduct",
    "accreditation", "accredited",
    "certification", "certified",
    "registration", "register", "registered",
    "renewal", "renew",
    "membership", "member",
    "subscription", "subscribe",
    "beneficiary", "beneficiaries",
    "entitlement", "entitled",
    "allowance", "allowances",
    "reimbursement", "reimburse", "reimbursable",
    "deduction", "deductions",
    "exemption", "exempt", "exempted",
    "waiver", "waive", "waived",
    "consent", "consents",
    "authorization", "authorize", "authorised",
    "approval", "approve", "approved",
    "application", "applicant", "applicants",
    "submission", "submit", "submitted",
    "deadline", "deadlines",
    "timeline", "timelines",
    "duration", "tenure",
    "term", "terms",
    "condition", "conditions",
    "requirement", "requirements", "require",
    "obligation", "obligations", "obligated",
    "responsibility", "responsibilities",
    "entitle", "entitled", "entitlement",
    "provision", "provisions",
    "stipend", "stipends",
    "honorarium",
    "remuneration",
    "compensation",
    "benefit", "benefits",
    "grant", "grants",
    "funding", "fund",
    "sponsor", "sponsorship", "sponsored",
    "bursary", "bursaries",
    "loan", "loans",
    "assistance", "assist",
    "support", "supported",
    "welfare",
    "concession", "concessions",
    "dispensation",
    "exception", "exceptions",
    "override", "overrides",
    "interpretation",
    "amendment", "amendments",
    "modification", "modifications",
    "revision", "revisions",
    "review", "reviews",
    "audit", "audits", "auditing",
    "inspection", "inspect",
    "monitoring", "monitor",
    "evaluation", "evaluate",
    "assessment", "assess",
    "verification", "verify", "verified",
    "enforcement", "enforce",
    "implementation", "implement",
    "effective date",
    "commencement",
    "transition", "transitional",
    "grandfather", "grandfathered",
    "retrospective", "retroactive",
    "application form",
    "declaration",
    "affidavit",
    "undertaking",
    "indemnity",
    "code of practice",
    "best practice",
    "standard practice",
    "industry standard",
    "quality assurance",
    "quality control",
    "due diligence",
    "risk assessment",
    "risk management",
    "safeguarding",
    "health and safety",
    "occupational health",
    "workplace",
    "harassment",
    "discrimination",
    "dignity",
    "inclusion", "inclusive",
    "diversity",
    "equality", "equal opportunity",
    "accessibility",
    "reasonable adjustment",
    "special needs",
    "learning support",
    "student support",
    "pastoral",
    "counselling", "counseling",
    "mental health",
    "wellbeing", "well-being",
    "welfare",
    "accommodation",
    "residence", "residential",
    "hall of residence",
    "dormitory",
    "mess",
    "catering",
    "meal plan",
    "transport",
    "shuttle",
    "library",
    "laboratory", "lab",
    "workshop",
    "seminar",
    "tutorial",
    "lecture",
    "attendance",
    "participation",
    "engagement",
    "placement",
    "internship", "intern",
    "trainee", "traineeship",
    "apprenticeship", "apprentice",
    "practicum",
    "clinical",
    "fieldwork", "field work",
    "research",
    "thesis", "dissertation",
    "project",
    "assignment",
    "examination", "exam", "exams",
    "assessment",
    "grade", "grading", "graded",
    "mark", "marks",
    "score", "scoring",
    "merit",
    "distinction",
    "classification",
    "award", "awards",
    "degree", "degrees",
    "diploma", "diplomas",
    "certificate", "certificates",
    "transcript", "transcripts",
    "credit", "credits",
    "module", "modules",
    "course", "courses",
    "program", "programme", "programs",
    "faculty",
    "department",
    "dean",
    "registrar",
    "principal",
    "director",
    "governing body",
    "board of",
    "committee",
    "council",
    "senate",
    "academic board",
    "student union",
    "student council",
    "parent teacher",
    "institution",
    "college",
    "university",
    "school",
    "institute",
    "academy",
    "hostel",
    "dorm",
    "lodging",
    "boarding",
}

CONTRACTUAL_SIGNALS: Set[str] = {
    "hereby agrees", "hereby agree",
    "hereinafter",
    "witnesseth",
    "in witness whereof",
    "by and between",
    "force majeure",
    "confidential information",
    "disclosing party", "receiving party",
    "indemnify", "indemnification", "indemnity",
    "governing law",
    "arbitration", "arbitrate",
    "binding effect", "binding arbitration",
    "entire agreement",
    "severability",
    "counterparts",
    "signature", "signed", "signatory",
    "warrant", "warranties", "warranty",
    "representation", "representations",
    "this agreement", "this contract",
    "shall be governed",
    "prevailing party",
    "confidentiality agreement",
    "non-disclosure agreement",
    "mutual confidentiality",
    "unilateral confidentiality",
    "dispute resolution",
    "joint venture",
    "memorandum of understanding",
    "letter of intent",
    "terms and conditions",
    "license agreement",
    "service level agreement",
    "hold harmless",
    "limitation of liability",
    "cap on liability",
    "aggregate liability",
    "consequential damages",
    "incidental damages",
    "specific performance",
    "injunctive relief",
    "attorneys fees",
    "legal fees",
    "prevailing party",
    "class action waiver",
    "jury waiver",
    "waiver of jury",
    "no oral modification",
    "entire understanding",
    "integration clause",
    "merger clause",
    "supersedes all prior",
    "exclusive remedy",
    "sole remedy",
    "irreparable harm",
    "irreparable injury",
}

POLICY_TYPE_KEYWORDS: Dict[str, Set[str]] = {
    "Administrative Rules": {
        "administrative", "administration", "rule", "rules",
        "regulation", "regulations", "regulatory", "directive", "directives",
        "order", "orders", "circular", "notification", "public notice",
        "official memorandum", "office order", "executive order",
    },
    "Procedures": {
        "procedure", "procedures", "procedural", "process", "processes",
        "workflow", "step", "steps", "instruction", "instructions",
        "standard operating procedure", "sop", "operating procedure",
        "protocol", "protocols", "methodology", "method",
    },
    "Eligibility Criteria": {
        "eligibility", "eligible", "ineligible", "criteria", "criterion",
        "qualification", "qualifications", "qualified", "prerequisite",
        "pre-requisite", "requirements", "requirement", "condition", "conditions",
        "entitlement", "entitled", "entitle",
    },
    "Guidelines": {
        "guideline", "guidelines", "guidance", "best practice", "good practice",
        "recommendation", "recommendations", "recommended", "advisory",
        "code of practice", "code of conduct", "framework",
    },
    "Rebate Policy": {
        "rebate", "rebates", "discount", "discounts", "cashback",
        "incentive", "incentives", "subsidy", "subsidies",
        "refund", "refunds", "refundable", "reimbursement",
        "concession", "concessions", "benefit", "benefits",
    },
    "Hostel Regulations": {
        "hostel", "dormitory", "dorm", "residence", "residential",
        "accommodation", "lodging", "boarding", "mess", "catering",
        "hall of residence", "student housing", "living quarters",
        "room", "rooms", "occupancy", "check-in", "check-out",
        "curfew", "visitor", "visitors", "guest", "guests",
    },
    "Academic Policies": {
        "academic", "curriculum", "curricular", "syllabus", "syllabi",
        "course", "courses", "program", "programme", "module", "modules",
        "admission", "enrollment", "enrolment", "registration",
        "examination", "exam", "grade", "grading", "assessment",
        "degree", "diploma", "certificate", "transcript",
        "credit", "credits", "tuition", "scholarship",
        "attendance", "participation", "placement", "internship",
        "thesis", "dissertation", "defense", "viva",
    },
    "Institutional Notice": {
        "notice", "notices", "notification", "announcement",
        "public notice", "official notice", "communication",
        "circular", "memorandum", "memo", "advisory",
        "information", "important notice", "attention",
    },
}

POLICY_STRUCTURE_PATTERNS = [
    re.compile(r"(?im)^\s*(?:policy|procedure|guideline|regulation|rule|protocol|code)\s+(?:no\.?|number|title|name|for|on|regarding|relating to|governing)\b"),
    re.compile(r"(?im)^\s*(?:scope|purpose|objective|background|definitions|definitions?)\s*[:\.]"),
    re.compile(r"(?im)^\s*(?:effective\s+date|date\s+of\s+effect|issued\s+by|approved\s+by|reviewed\s+by|authority)\s*[:\.]"),
    re.compile(r"(?im)^\s*(?:1\.\s*(?:purpose|scope|introduction|background|definitions|objective))"),
    re.compile(r"(?im)(?:this\s+(?:policy|procedure|guideline|regulation|code|framework))\s+(?:sets?\s+out|applies\s+to|governs?|establishes?|defines?|provides?\s+(?:for|guidance))\b"),
    re.compile(r"(?im)(?:who\s+(?:is|are)\s+(?:eligible|covered|affected|responsible|required))"),
    re.compile(r"(?im)(?:non-compliance|noncompliance|failure to comply|breach of (?:policy|regulation|rules))\b"),
    re.compile(r"(?im)(?:effective\s+(?:from|immediately|upon|as of)|commencement\s+date|comes?\s+into\s+(?:effect|force))\b"),
    re.compile(r"(?im)^\s*(?:appendix|annexure|schedule|form|annex)\s+[A-Z0-9]"),
    re.compile(r"(?im)(?:review\s+(?:period|cycle|date|process)|amendment\s+(?:procedure|process|policy))\b"),
    re.compile(r"(?im)(?:appeal\s+(?:process|procedure|mechanism)|grievance\s+(?:process|procedure|mechanism|redressal))\b"),
    re.compile(r"(?im)(?:disciplinary\s+(?:action|proceedings|procedure|process|measures))\b"),
    re.compile(r"(?im)(?:student|employee|staff|faculty|member|participant|applicant|resident)\s+(?:shall|must|should|may|will|are\s+(?:required|expected|obliged|responsible))\b"),
    re.compile(r"(?im)(?:rights?\s+(?:and\s+)?responsibilities|duties\s+(?:and\s+)?obligations)\b"),
    re.compile(r"(?im)^\s*(?:PART|SECTION|CHAPTER|CLAUSE|RULE|POLICY|ANNEXURE|APPENDIX)\s+[IVXLCDM0-9]"),
    re.compile(r"(?im)\b(?:institution|authority|governing\s+body|management|administration)\s+(?:shall|may|will|must|reserves?\s+the\s+right)\b"),
    re.compile(r"(?im)(?:refund|rebate|concession|exemption|waiver)\s+(?:policy|procedure|rules|guidelines)\b"),
    re.compile(r"(?im)\b(?:applicant|student|employee|staff|resident|member|beneficiary|participant)\s+(?:must\s+(?:submit|provide|complete|submit|attach|enclose|ensure)|shall\s+(?:submit|provide|complete|ensure))\b"),
]


POLICY_EXPLANATIONS: Dict[str, str] = {
    "Administrative Rules": "This document contains administrative rules, directives, or official orders that govern institutional operations rather than contractual obligations between parties.",
    "Procedures": "This document describes step-by-step procedures or standard operating processes, outlining how tasks should be performed rather than establishing contractual rights.",
    "Eligibility Criteria": "This document defines eligibility criteria or qualification requirements for a program, benefit, or opportunity, rather than constituting a binding agreement.",
    "Guidelines": "This document provides guidelines, recommendations, or best practices to inform decision-making rather than establishing legally enforceable terms.",
    "Rebate Policy": "This document outlines a rebate, discount, or incentive program structure with eligibility and claiming procedures, not a contractual agreement.",
    "Hostel Regulations": "This document contains hostel or residential accommodation regulations governing occupant conduct and facility use rather than contractual terms.",
    "Academic Policies": "This document sets forth academic policies, curriculum rules, examination procedures, or degree requirements for an educational institution.",
    "Institutional Notice": "This document is an institutional notice, announcement, or official communication providing information rather than contractual terms.",
    "General Policy": "This document contains policy or procedural rules that establish standards, requirements, or guidelines rather than creating a legally binding contract.",
}


def detect_policy_type(text: str) -> tuple[str, float, List[str]]:
    """Detect the specific policy type based on keyword matches."""
    text_lower = text.lower()
    best_type = "General Policy"
    best_score = 0.0
    matched_keywords: List[str] = []

    for policy_type, keywords in POLICY_TYPE_KEYWORDS.items():
        score = 0.0
        type_matches: List[str] = []
        for keyword in keywords:
            count = len(re.findall(re.escape(keyword), text_lower))
            if count > 0:
                score += count * (1.0 / len(keywords))
                if keyword not in type_matches:
                    type_matches.append(keyword)
        if score > best_score:
            best_score = score
            best_type = policy_type
            matched_keywords = type_matches

    return best_type, best_score, matched_keywords


def _get_words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z]{3,}", text.lower())


def compute_policy_keyword_score(text: str) -> tuple[float, List[str]]:
    if not text or not text.strip():
        return 0.0, []
    text_lower = text.lower()
    words = _get_words(text)
    if not words:
        return 0.0, []

    total_matches = 0
    matched_keywords: List[str] = []
    for keyword in POLICY_KEYWORDS:
        if len(keyword.split()) > 1:
            count = len(re.findall(re.escape(keyword), text_lower))
            if count > 0:
                total_matches += count
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)
        else:
            count = sum(1 for w in words if w == keyword)
            if count > 0:
                total_matches += count
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)

    return total_matches / len(words), matched_keywords


def compute_contractual_signal_score(text: str) -> tuple[float, List[str]]:
    if not text or not text.strip():
        return 0.0, []
    text_lower = text.lower()
    words = _get_words(text)
    if not words:
        return 0.0, []

    total_matches = 0
    matched_signals: List[str] = []
    for signal in CONTRACTUAL_SIGNALS:
        if len(signal.split()) > 1:
            count = len(re.findall(re.escape(signal), text_lower))
            if count > 0:
                total_matches += count
                if signal not in matched_signals:
                    matched_signals.append(signal)
        else:
            count = sum(1 for w in words if w == signal)
            if count > 0:
                total_matches += count
                if signal not in matched_signals:
                    matched_signals.append(signal)

    return total_matches / len(words), matched_signals


def compute_policy_structure_score(text: str) -> float:
    if not text or not text.strip():
        return 0.0
    matches = sum(1 for pattern in POLICY_STRUCTURE_PATTERNS if pattern.search(text))
    max_possible = len(POLICY_STRUCTURE_PATTERNS)

    raw_score = matches / max_possible

    if matches >= 3:
        raw_score = min(1.0, raw_score * 1.3)
    if matches >= 6:
        raw_score = min(1.0, raw_score * 1.2)

    return raw_score


POLICY_SUPPRESSION_MESSAGE = (
    "This document appears to be a policy, procedure, or administrative notice "
    "rather than a contractual agreement. Policy documents are not routed through "
    "the legal-risk audit pipeline. The document has been classified as: {policy_type}"
)


def detect_policy_document(text: str) -> PolicyDetectionResult:
    """Detect whether input text is a policy/procedure document.

    Returns a PolicyDetectionResult with classification, confidence,
    and detailed factor breakdown.
    """
    if not text or not text.strip():
        return PolicyDetectionResult(
            detection=PolicyDetection.NOT_POLICY,
            confidence=0.0,
            policy_keyword_score=0.0,
            contractual_signal_score=0.0,
            policy_type="General Policy",
            matched_policy_keywords=[],
            matched_contractual_signals=[],
            explanation="Empty or blank text.",
        )

    policy_score, matched_policy_keywords = compute_policy_keyword_score(text)
    contractual_score, matched_contractual_signals = compute_contractual_signal_score(text)
    structure_score = compute_policy_structure_score(text)
    policy_type, type_score, type_keywords = detect_policy_type(text)

    policy_signal = (
        policy_score * 0.40 +
        structure_score * 0.35 +
        type_score * 0.25
    )

    effective_signal = policy_signal - (contractual_score * 0.5)
    effective_signal = max(0.0, effective_signal)

    is_clearly_policy = (
        policy_signal >= POLICY_KEYWORD_THRESHOLD
        and contractual_score < CONTRACTUAL_SIGNAL_THRESHOLD
        and (policy_signal / max(contractual_score, 0.001)) >= POLICY_DOMINANCE_RATIO
    )

    is_strongly_policy = (
        policy_signal >= POLICY_KEYWORD_THRESHOLD * 2
        and contractual_score < CONTRACTUAL_SIGNAL_THRESHOLD * 1.5
    )

    if is_clearly_policy or is_strongly_policy:
        detection = PolicyDetection.POLICY
        confidence = min(1.0, effective_signal * 3.0)
    elif policy_signal >= POLICY_KEYWORD_THRESHOLD and contractual_score > CONTRACTUAL_SIGNAL_THRESHOLD:
        detection = PolicyDetection.UNCLEAR
        confidence = effective_signal
    else:
        detection = PolicyDetection.NOT_POLICY
        confidence = effective_signal

    explanation = POLICY_EXPLANATIONS.get(policy_type, POLICY_EXPLANATIONS["General Policy"])

    logger.info(
        "[PolicyDetection] detection=%s confidence=%.4f policy_score=%.4f "
        "contractual_score=%.4f structure_score=%.4f type_score=%.4f "
        "policy_signal=%.4f effective_signal=%.4f policy_type=%s",
        detection.value, confidence, policy_score, contractual_score,
        structure_score, type_score, policy_signal, effective_signal, policy_type,
    )

    return PolicyDetectionResult(
        detection=detection,
        confidence=confidence,
        policy_keyword_score=policy_score,
        contractual_signal_score=contractual_score,
        policy_type=policy_type,
        matched_policy_keywords=matched_policy_keywords[:10],
        matched_contractual_signals=matched_contractual_signals[:10],
        explanation=explanation,
        factors={
            "policy_keyword_score": round(policy_score, 4),
            "contractual_signal_score": round(contractual_score, 4),
            "structure_score": round(structure_score, 4),
            "type_score": round(type_score, 4),
            "policy_signal": round(policy_signal, 4),
            "effective_signal": round(effective_signal, 4),
            "policy_type_score": round(type_score, 4),
        },
    )
