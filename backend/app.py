from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import Dict, Optional
from dataclasses import dataclass
import ollama
import time
import re
from fastapi import UploadFile, File, Form
import pymupdf 
from backend.config import settings
from backend.logger import logger
# RAG integration temporarily disabled; keep import commented for future use.
# from backend.rag import query

ollama_client = ollama.Client(host="http://host.docker.internal:11434")

# =====================
# Data Models
# =====================
@dataclass
class ValidationResult:
    """Result of response validation containing validation status and details."""
    is_valid: bool
    violation_type: Optional[str] = None
    violation_reason: Optional[str] = None
    refusal_message: Optional[str] = None

@dataclass
class ValidationContext:
    """Context information needed for response validation."""
    user_input: str
    session_mode: str
    is_creator_question: bool

# =====================
# App
# =====================
app = FastAPI(title="Zynexra API")

CREATOR_STATEMENT = (
    "I was created by Jay Lanjewar."
)

# =====================
# Validation Engine
# =====================
class ValidationEngine:
    """Validates complete responses without triggering regeneration."""
    
    def __init__(self):
        # Detect only first-person AI identity disclosures.
        # This intentionally allows neutral/academic terminology such as "language model".
        self.identity_disclosure_patterns = [
            re.compile(
                r"\b(?:as\s+an?\s+|i\s*(?:am|'m)\s+an?\s+)"
                r"(?:ai|artificial\s+intelligence|language\s+model|llm|chatbot|assistant)\b",
                re.IGNORECASE
            ),
            re.compile(
                r"\b(?:i\s*(?:am|'m)\s+)(?:a\s+)?(?:large\s+)?language\s+model\b",
                re.IGNORECASE
            ),
            re.compile(
                r"\b(?:i\s+was\s+(?:created|built|trained)\s+as\s+an?\s+)"
                r"(?:ai|assistant|language\s+model)\b",
                re.IGNORECASE
            ),
        ]
        
    def validate_response(self, response: str, context: ValidationContext) -> ValidationResult:
        """Validate complete response against all rules.
        
        Args:
            response: Complete response string to validate
            context: Validation context with user input and session info
            
        Returns:
            ValidationResult with validation status and details
        """
        try:
            # Input validation
            if not response or not isinstance(response, str):
                return ValidationResult(
                    is_valid=False,
                    violation_type="validation_error",
                    violation_reason="Invalid response format for validation",
                    refusal_message="[SYSTEM ERROR] Response validation failed due to invalid format."
                )
            
            response_lower = response.lower()
            
            # 1. Identity Check (Creator Name Integrity)
            if "lanjewar" in context.user_input.lower() and "jay" not in response_lower:
                return ValidationResult(
                    is_valid=False,
                    violation_type="identity_guard",
                    violation_reason="Identity guard failure: Must state creator exactly.",
                    refusal_message="[SYSTEM REFUSAL] Response rejected due to identity guard violation."
                )
            
            # 2. First-person AI identity disclosure check
            for pattern in self.identity_disclosure_patterns:
                if pattern.search(response):
                    return ValidationResult(
                        is_valid=False,
                        violation_type="identity_disclosure",
                        violation_reason=f"Contains first-person AI identity disclosure matching pattern: '{pattern.pattern}'",
                        refusal_message="[SYSTEM REFUSAL] Response rejected due to compliance violation: First-person AI identity disclosure detected."
                    )
            
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            # Graceful handling of validation engine failures
            return ValidationResult(
                is_valid=False,
                violation_type="validation_error",
                violation_reason=f"Validation engine error: {str(e)}",
                refusal_message="[SYSTEM ERROR] Response validation failed due to internal error."
            )
    
    def get_refusal_message(self, violation_type: str, reason: str) -> str:
        """Generate appropriate refusal message for violation with optimized performance.
        
        Args:
            violation_type: Type of validation violation
            reason: Specific reason for the violation
            
        Returns:
            Formatted refusal message (returned immediately)
        """
        # Pre-formatted refusal messages for immediate return - no processing delays
        return f"[SYSTEM REFUSAL] Response rejected due to compliance violation: {reason}."

# =====================
# Response Generator
# =====================
class ResponseGenerator:
    """Handles single-pass model generation with streaming collection."""
    
    def __init__(self):
        pass
    
    def generate_response(self, messages: list, model: str) -> str:
        """Generate complete response from model in single pass.
        
        Args:
            messages: List of message dictionaries for the model
            model: Model name to use for generation
            
        Returns:
            Complete response string from the model
            
        Raises:
            HTTPException: If model communication fails
        """
        try:
            return self._generate_with_model(messages, model)
        except HTTPException as e:
            if self._should_fallback(e):
                logger.warning("Model fallback activated. Switching to %s", settings.MODEL_FALLBACK)
                return self._generate_with_model(messages, settings.MODEL_FALLBACK)
            raise
    
    def _should_fallback(self, error: HTTPException) -> bool:
        """Determine if a fallback model should be used."""
        detail = getattr(error, "detail", "")
        detail_lower = str(detail).lower()

        if error.status_code == 504 or "timeout" in detail_lower:
            return True

        # Fallback on upstream model/runtime failures.
        if error.status_code in {500, 503} and any(
            token in detail_lower for token in [
                "model",
                "ollama",
                "communication error",
                "service unavailable",
                "connection",
                "stream",
            ]
        ):
            return True

        if "model" in detail_lower and any(token in detail_lower for token in ["not found", "no such", "pull", "missing"]):
            return True

        return False
    
    def _generate_with_model(self, messages: list, model: str) -> str:
        """Generate complete response from a specific model in single pass.
        
        Args:
            messages: List of message dictionaries for the model
            model: Model name to use for generation
            
        Returns:
            Complete response string from the model
            
        Raises:
            HTTPException: If model communication fails
        """
        try:
            # Single model call - no retries
            stream = ollama_client.chat(
                model=model,
                messages=messages,
                stream=True,
                options={"temperature": 0,
                         "num_ctx": 4096}
            )
            
            buffer = ""
            for chunk in stream:
                if chunk is None:
                    raise HTTPException(500, "Model communication error: Received null chunk")
                
                content = chunk.get("message", {}).get("content", "")
                if content:
                    buffer += content
            
            # Ensure we got some response
            if not buffer.strip():
                raise HTTPException(500, "Model communication error: Empty response received")
                    
            return buffer
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except ConnectionError as e:
            logger.error("Model service connection failed: %s", e)
            raise HTTPException(503, f"Model service unavailable: {str(e)}")
        except TimeoutError as e:
            logger.error("Model request timed out: %s", e)
            raise HTTPException(504, f"Model request timeout: {str(e)}")
        except Exception as e:
            # Catch all other exceptions and convert to HTTP 500
            logger.error("Unexpected model communication error: %s", e)
            raise HTTPException(500, f"Model communication error: {str(e)}")
    
    def stream_to_user(self, content: str):
        yield content

# =====================
# Session Manager
# =====================
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}

    def get(self, sid: str) -> Dict:
        if sid not in self.sessions:
            self.sessions[sid] = {
                "history": [],
                "mode": "AUDIT",
                "created_at": time.time()
            }
        return self.sessions[sid]
    
    def should_update_history(self, validation_result: ValidationResult) -> bool:
        """Determine if response should be stored in history based on validation results.
        
        Args:
            validation_result: Result from ValidationEngine containing validation status
            
        Returns:
            True if response should be stored in history, False otherwise
        """
        return validation_result.is_valid
    
    def add_valid_exchange(self, session_id: str, user_input: str, assistant_response: str):
        """Add only validated exchanges to history.
        
        Args:
            session_id: Session identifier
            user_input: User's input message
            assistant_response: Assistant's validated response
        """
        session = self.get(session_id)
        session["history"].append({
            "user": user_input,
            "assistant": assistant_response
        })

sessions = SessionManager()
validation_engine = ValidationEngine()
response_generator = ResponseGenerator()

# =====================
# Models
# =====================
class Query(BaseModel):
    question: str
    session_id: str
    mode: Optional[str] = None
    task_anchor: Optional[str] = None

# =====================
# Helpers
# =====================
def is_creator_question(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in [
        "who made you",
        "who created you",
        "who built you",
        "who is your creator",
    ])

def pre_redact_pii(text: str) -> str:
    """Deterministically redact obvious PII before model invocation."""
    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+.[a-zA-Z]+")
    phone_pattern = re.compile(r"\+?\d[\d\s-]{7,}")
    name_pattern = re.compile(r"[A-Z][a-z]+\s[A-Z][a-z]+")
    address_pattern = re.compile(
        r"\d+\s+[A-Za-z]+\s+(Street|St|Road|Rd|Terrace|Avenue|Ave|Lane|Ln|Drive|Dr|Boulevard|Blvd)",
        re.IGNORECASE,
    )

    text = name_pattern.sub("[REDACTED]", text)
    text = email_pattern.sub("[REDACTED]", text)
    text = phone_pattern.sub("[REDACTED]", text)
    text = address_pattern.sub("[REDACTED]", text)
    return text

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

def normalize_issue_categories_and_language(response_text: str) -> str:
    """Normalize category labels and enforce deterministic rewrite safeguards."""
    if "Issue:" not in response_text:
        return response_text

    issue_pattern = re.compile(r"(?ims)^Issue:\s*.*?(?=^Issue:\s*|\Z)")
    category_replacements = {
        "Indemnification Risk": "Indemnification",
        "Indemnification Exposure": "Indemnification",
        "Structural Conflict": "Structural Inconsistency",
        "Residuals Risk": "Residuals",
        "Governing Law Risk": "Governing Law",
    }
    unlimited_tokens = re.compile(r"\b(unlimited|uncapped|no cap|no limit)\b", re.IGNORECASE)

    def replace_section(block: str, label: str, new_text: str) -> str:
        pattern = re.compile(
            rf"(?is)({re.escape(label)}:\s*)(.*?)(?=\n[A-Z][A-Za-z ]+:\s|$)"
        )
        return pattern.sub(lambda m: f"{m.group(1)}{new_text}", block, count=1)

    def apply_normalization(block: str) -> str:
        # Category normalization
        for old, new in category_replacements.items():
            block = re.sub(
                rf"(?im)^(Category:\s*){re.escape(old)}\b",
                rf"\1{new}",
                block,
                count=1
            )

        # Extract fields
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
        category_match = re.search(r"(?im)^Category:\s*(.+)", block)

        quoted_text = quoted_match.group(1).strip() if quoted_match else ""
        suggested_text = suggested_match.group(2).strip() if suggested_match else ""
        category_text = category_match.group(1).strip() if category_match else ""

        # Confidentiality rewrite safeguard
        if "CONFIDENTIALITY" in category_text.upper() and suggested_text:
            if re.search(r"\bterminate\b|\btermination\b|end confidentiality", suggested_text, re.IGNORECASE):
                corrected = ("Ensure confidentiality obligations survive termination and remain "
                             "enforceable after contract expiration.")
                block = replace_section(block, "Suggested Improvement", corrected)

        # Indemnification cap enforcement
        if "INDEMNIFICATION" in category_text.upper():
            if unlimited_tokens.search(quoted_text):
                cap_text = "Introduce a liability cap so indemnification obligations are capped at a defined monetary amount."
                block = replace_section(block, "Suggested Improvement", cap_text)

        return block

    return issue_pattern.sub(lambda m: apply_normalization(m.group(0)), response_text)

def normalize_issue_output(response_text: str) -> str:
    """Normalize categories and language for deterministic outputs."""
    if "Issue:" not in response_text:
        return response_text

    issue_pattern = re.compile(r"(?ims)^Issue:\s*.*?(?=^Issue:\s*|\Z)")
    unlimited_tokens = re.compile(r"\b(unlimited|uncapped|no cap|no limit)\b", re.IGNORECASE)
    unlimited_word = re.compile(r"\bunlimited\b", re.IGNORECASE)

    def replace_section(block: str, label: str, new_text: str) -> str:
        pattern = re.compile(
            rf"(?is)({re.escape(label)}:\s*)(.*?)(?=\n[A-Z][A-Za-z ]+:\s|$)"
        )
        return pattern.sub(lambda m: f"{m.group(1)}{new_text}", block, count=1)

    def apply_normalization(block: str) -> str:
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
        risk_changed = False
        suggested_changed = False

        # 0. Global unlimited sanitization outside quoted text
        if unlimited_word.search(risk_text):
            risk_text = unlimited_word.sub("uncapped", risk_text)
            risk_changed = True
        if unlimited_word.search(suggested_text):
            suggested_text = unlimited_word.sub("uncapped", suggested_text)
            suggested_changed = True

        # 1. Category normalization (Category line only)
        new_category = category_text
        if category_lower == "liability exposure" and "indemn" in quoted_text.lower():
            new_category = "Indemnification"
        elif category_lower == "indemnification risk":
            new_category = "Indemnification"
        elif category_lower == "structural conflict":
            new_category = "Structural Inconsistency"
        elif category_lower == "residuals risk":
            new_category = "Residuals"
        elif category_lower == "governing law risk":
            new_category = "Governing Law"

        if new_category != category_text and category_match:
            block = re.sub(
                r"(?im)^(Category:\s*).+$",
                rf"\1{new_category}",
                block,
                count=1
            )
            category_text = new_category
            category_lower = new_category.lower()

        # 2. Structural conflict normalization based on quoted or risk language
        if re.search(r"\b(conflict|contradict|inconsistent|incompatible)\b", risk_text, re.IGNORECASE) or \
           re.search(r"\b(conflict|contradict|inconsistent|incompatible)\b", quoted_text, re.IGNORECASE):
            if category_text != "Structural Inconsistency":
                block = re.sub(
                    r"(?im)^(Category:\s*).+$",
                    r"\1Structural Inconsistency",
                    block,
                    count=1
                )
                category_text = "Structural Inconsistency"
                category_lower = category_text.lower()

        # 3. Residuals language cleanup
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

        # 4. Confidentiality rewrite safeguard
        if "confidentiality" in category_lower:
            conf_text = "Ensure confidentiality obligations survive termination and continue after contract expiration."
            suggested_text = conf_text
            block = replace_section(block, "Suggested Improvement", suggested_text)

        # 5. Enforce cap wording for indemnification with unlimited cues
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

    return issue_pattern.sub(lambda m: apply_normalization(m.group(0)), response_text)

# =====================
# Prompts
# =====================
# =====================
# ABSOLUTE IDENTITY GUARD (Non-Overrideable)
# =====================
IDENTITY_GUARD = """IDENTITY RULES (ABSOLUTE - NON-NEGOTIABLE):
- You are Zynexra, a privacy-first, offline AI system.
- You were created by Jay Lanjewar.
- You MUST NEVER claim to be your creator.
- You MUST NEVER invent organizations (e.g., "Zynexra Labs", "Zynexra Inc.").
- You MUST NEVER invent backstories, origins, or symbolic meanings about yourself.
- You are real software, not mythological or fictional.
- You are OFFLINE. You do not have internet access.
- You do NOT browse or fetch online data.
- Output must be formal, neutral, and professional.
- NEVER use the phrase "I apologize for any confusion".
- NEVER say "As an AI" or "I am an AI language model".
"""

# =====================
# ISOLATED PROMPT BUILDERS
# =====================

def build_audit_prompt() -> str:
    return IDENTITY_GUARD + """MODE: AUDIT
You are an offline legal document risk analysis engine designed for small to medium law firms.

Your job is to identify:
Legal risk exposure
Ambiguous or vague clauses
Missing critical clauses
Enforcement weaknesses
Privacy or confidentiality risks
Liability escalation points
Structural inconsistencies

CORE TASK:
Critically evaluate the uploaded document strictly for legal and structural risk.

REQUIREMENTS (MANDATORY):
Quote specific sentences or phrases.
Do NOT give generic advice.
Provide a precise rewrite whenever possible.
Do not produce summaries.
Do not soften risk language.
Prioritize risk detection over tone correction.

SEVERITY RULES:
- If the clause materially weakens enforceability or creates unlimited exposure, Severity must not be lower than HIGH.
- If confidentiality obligations terminate completely, Severity must be CRITICAL.
- If indemnification or liability is explicitly uncapped or unlimited in the clause text, Severity MUST be CRITICAL.
- Limit total issues to the most material 8.

Before generating each issue:
1. Confirm the quoted text matches the identified clause category.
2. Confirm which party is exposed (Discloser or Recipient).
3. Do not mislabel clause numbers or categories.
4. If uncertainty exists, state uncertainty explicitly.

Allowed Categories (use EXACT wording):
- Liability Exposure
- Indemnification Risk
- Enforceability Weakness
- Structural Omission
- Negotiation Imbalance
- Privacy Risk
- Confidentiality Termination
- Governing Law
- Governing Law Risk
- Structural Inconsistency
- Structural Conflict
- Residuals
- Residuals Risk
Use ONLY one of the allowed categories above. Do not invent new category names.

STRICT CATEGORY LANGUAGE RULE:
If Category is NOT one of:
- Liability Exposure
- Indemnification Risk
Then the Risk Explanation MUST NOT contain: liability, liable, indemnify, damages, exposure, unlimited.
If those words are used in non-liability categories, the issue is invalid.

If the issue does not involve financial risk, do not describe it using financial terminology.
Use liability terms only when the clause involves financial exposure, indemnification, damages, or limitation of liability.
Do not generate multiple issues for the same clause unless they represent materially distinct risk categories.
If a clause contains uncapped or unlimited indemnification or liability in the Quoted Text, Suggested Improvement MUST include at least one of the following exact phrases:
- capped at
- limited to
- shall not exceed
- aggregate cap
- maximum amount of
General wording such as 'clarify scope' or 'narrow liability' is insufficient.
ABSOLUTE RULE:
Before finalizing output, scan all issues.
If any two issues contain identical Quoted Text, you MUST merge them into a single issue.

If a clause contains:
- a clearly defined monetary liability cap,
- mutual or balanced indemnity structure,
- and a defined survival period for confidentiality,
it MUST NOT be flagged as HIGH or CRITICAL.
Strong protective clauses are not risks unless they create imbalance, unenforceability, or regulatory conflict.

Before generating the Risk Explanation, explicitly determine:
1. Which party bears the obligation?
2. Which party benefits?
3. Which party is exposed if the clause is enforced as written?

The word "unlimited" MUST NOT appear anywhere in the output unless the Quoted Text contains one of the following exact phrases:
- unlimited
- uncapped
- no cap
- no limit
If none of those phrases appear in the Quoted Text, the word "unlimited" is prohibited.
Suggested Improvement must preserve or strengthen confidentiality survival obligations. It must not reduce survival duration or introduce earlier termination.
If the clause does not terminate confidentiality, do not describe it as termination.

Suggested improvements must reflect commercially realistic negotiation standards.
Do not default to removing clauses unless the clause is fundamentally unlawful or structurally defective.
For each issue, use this exact structure:
Issue:
Severity: LOW / MEDIUM / HIGH / CRITICAL
Category: (Choose one of the defined categories above)
Location: (Clause number, heading, or paragraph reference)
Quoted Text:
Risk Explanation:
Suggested Improvement:

Do not combine distinct clauses into a single issue.
However, identical quoted text must never appear more than once.

If the document lacks clause numbering, reference paragraph position.

TONE:
Professional, precise, risk-focused.
"""

def build_redaction_prompt() -> str:
    """REDACTION: Privacy shield, auto-redacts PII."""
    return IDENTITY_GUARD + """MODE: REDACTION
MODE: REDACTION

You are a privacy redaction engine.

RULES:

1. Detect personal identifiable information (PII).
2. Replace sensitive information with [REDACTED].
3. Output ONLY the redacted text.
4. Do NOT explain what was redacted.
5. Do NOT add commentary or summaries.
6. If a full personal name appears (e.g., FirstName LastName), replace the name with [REDACTED].

OUTPUT FORMAT RULE:
Return only the redacted text. Do not include explanations such as "data was redacted" or "sensitive information detected".
"""

def build_advisory_prompt() -> str:
    """ADVISORY: General legal practice guidance (no document analysis)."""
    return IDENTITY_GUARD + """MODE: ADVISORY
SCOPE RULE (STRICT):

You ONLY assist with questions related to legal practice, contracts, and legal terminology.

If a request is unrelated to legal practice, you MUST refuse.

Examples of requests you must refuse:
- writing emails
- personal writing tasks
- coding
- school assignments
- poems or creative writing
- general conversation unrelated to law
DOCUMENT GENERATION RULE:

You may provide short example clauses for educational purposes.

You must NOT generate complete legal agreements, contracts, or legally binding documents.

If asked to generate a full legal document, respond:

"Zynexra does not generate full legal agreements. I can explain contract structures or provide example clauses for study purposes."
When explaining topics, prefer structured bullet points or numbered sections.
When listing examples:
- Provide a maximum of 8 items.
- Do not repeat items.
- Each item must appear only once.

When refusing, respond with:

"This request is outside Zynexra's advisory scope. I assist only with legal practice and contract-related questions."
"""

def build_execution_prompt(mode: str) -> str:
    """Route to isolated prompt builders based on execution mode."""
    if mode == "AUDIT":
        return build_audit_prompt()
    elif mode == "REDACTION":
        return build_redaction_prompt()
    elif mode == "ADVISORY":
        return build_advisory_prompt()
    else:
        # Default to AUDIT for any unknown or default mode
        return build_audit_prompt()

# =====================
# Additional Models
# =====================
class SetModeRequest(BaseModel):
    session_id: str
    mode: str

# =====================
# Mode Endpoints
# =====================
@app.post("/set_mode")
def set_mode(req: SetModeRequest):
    session = sessions.get(req.session_id)
    normalized_mode = req.mode.upper()
    if normalized_mode not in {"AUDIT", "REDACTION", "ADVISORY"}:
        raise HTTPException(400, "Invalid mode. Allowed modes: AUDIT, REDACTION, ADVISORY")
    session["mode"] = normalized_mode
    return {"mode": session["mode"]}

@app.get("/get_mode")
def get_mode(session_id: str):
    session = sessions.get(session_id)
    return {"mode": session["mode"]}

@app.post("/export_report")
def export_report(session_id: str = Form(...)):
    session = sessions.get(session_id)

    report_text = session.get("last_report")

    if not report_text:
        raise HTTPException(400, "No report available to export.")

    return Response(
        content=report_text,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=zynexra_report.txt"
        }
    )

# =====================
# Endpoint
# =====================
@app.post("/ask")
def ask(q: Query):
    if not q.session_id:
        raise HTTPException(422, "session_id required")

    logger.info("Incoming /ask request. session_id=%s", q.session_id)

    session = sessions.get(q.session_id)
    text = q.question.strip()

    # -----------------
    # Creator identity (backend enforced)
    # -----------------
    if is_creator_question(text):
        return StreamingResponse(
            iter([CREATOR_STATEMENT]),
            media_type="text/plain"
        )

    # -----------------
    # Mode update
    # -----------------
    if q.mode:
        normalized_mode = q.mode.upper()
        if normalized_mode not in {"AUDIT", "REDACTION", "ADVISORY"}:
            raise HTTPException(400, "Invalid mode. Allowed modes: AUDIT, REDACTION, ADVISORY")
        session["mode"] = normalized_mode

    if session["mode"] == "REDACTION":
        text = pre_redact_pii(text)

    # -----------------
    # Build prompt
    # -----------------
    system_prompt = build_execution_prompt(session["mode"])

    # Inject task anchor if provided (e.g. for file uploads)
    if q.task_anchor:
        system_prompt = f"{q.task_anchor}\n\n{system_prompt}"

    messages = [{"role": "system", "content": system_prompt}]
    for turn in session["history"]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    messages.append({"role": "user", "content": text})

    # -----------------
    # Streaming response
    # -----------------
    def generate():
        # Send immediate heartbeat so connection stays open
        yield ""
        # Always try fast model first. ResponseGenerator handles fallback internally.
        try:
            complete_response = response_generator.generate_response(messages, settings.MODEL_FAST)
            complete_response = normalize_issue_severity(complete_response)
            complete_response = normalize_issue_output(complete_response)
        except HTTPException as http_err:
            # Re-raise HTTP exceptions from ResponseGenerator with proper error format
            raise http_err
        except Exception as e:
            # Handle any unexpected errors during generation
            logger.error("Unexpected error during /ask generation. session_id=%s error=%s", q.session_id, e)
            raise HTTPException(500, f"Unexpected error during generation: {str(e)}")
        
        # Post-generation validation using ValidationEngine
        try:
            validation_context = ValidationContext(
                user_input=text,
                session_mode=session["mode"],
                is_creator_question=is_creator_question(text)
            )
            
            validation_result = validation_engine.validate_response(complete_response, validation_context)
        except Exception as e:
            # Handle validation engine failures gracefully
            logger.error("Validation error during /ask. session_id=%s error=%s", q.session_id, e)
            raise HTTPException(500, f"Validation error: {str(e)}")
        
        if validation_result.is_valid:
            # Stream the valid response to user
            try:
                for char in response_generator.stream_to_user(complete_response):
                    yield char
                final_response = complete_response
                session["last_report"] = complete_response
                
                # Only store valid responses in conversation history using SessionManager
                if sessions.should_update_history(validation_result):
                    sessions.add_valid_exchange(q.session_id, text, final_response)
            except Exception as e:
                # Handle streaming errors gracefully
                yield f"[SYSTEM ERROR] Streaming error: {str(e)}"
                return
        else:
            # Stream refusal message immediately after validation
            try:
                refusal_message = validation_result.refusal_message or validation_engine.get_refusal_message(
                    validation_result.violation_type, validation_result.violation_reason
                )
                # Immediate streaming of refusal message
                for char in response_generator.stream_to_user(refusal_message):
                    yield char
            except Exception as e:
                # Handle refusal message streaming errors
                yield f"[SYSTEM ERROR] Error generating refusal message: {str(e)}"
            # Don't store failed responses in history - return immediately
            return

    return StreamingResponse(generate(), media_type="text/plain")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file in memory."""
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        logger.error("PDF extraction failed: %s", e)
        raise HTTPException(400, f"PDF processing error: {str(e)}")

@app.post("/ask_file")
def ask_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    mode: Optional[str] = Form(None)
):
    # ---- VALIDATION ----
    try:
        session = sessions.get(session_id)

        filename = file.filename.lower() if file.filename else ""
        logger.info("Uploaded file received. session_id=%s filename=%s", session_id, filename)
        
        if not filename.endswith((".txt", ".pdf")):
            raise HTTPException(400, "Only .txt and .pdf files supported")

        logger.info("Starting file processing. session_id=%s filename=%s", session_id, filename)
        content = file.file.read()
        if not content:
            raise HTTPException(400, "Empty file")
            
        file.file.close()

        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(content)
        else:
            # Default to .txt processing
            try:
                text = content.decode("utf-8", errors="ignore")
            except Exception as e:
                logger.error("File encoding error. session_id=%s filename=%s error=%s", session_id, filename, e)
                raise HTTPException(400, f"File encoding error: {str(e)}")

        if len(text) > 20000:
            raise HTTPException(400, "Document too large. Please upload a smaller file.")
        
        if mode:
            normalized_mode = mode.upper()
            if normalized_mode not in {"AUDIT", "REDACTION", "ADVISORY"}:
                raise HTTPException(400, "Invalid mode. Allowed modes: AUDIT, REDACTION, ADVISORY")
        else:
            normalized_mode = None

        effective_mode = normalized_mode if normalized_mode else session["mode"]

        if effective_mode == "ADVISORY":
            raise HTTPException(400, "File analysis is not supported in ADVISORY mode.")

        if effective_mode == "REDACTION":
            text = pre_redact_pii(text)
         
        # Build isolated messages for file analysis (no history)
        # -------------------------
        # RAG Retrieval Layer (disabled; uncomment when re-enabling RAG)
        # -------------------------
        # retrieved = rag_query(text, n_results=3)
        # 
        # retrieved_chunks = []
        # if retrieved and "documents" in retrieved:
        #     for doc_list in retrieved["documents"]:
        #         for chunk in doc_list:
        #             retrieved_chunks.append(chunk)
        #
        # rag_context = "\n\n".join(retrieved_chunks)
        rag_context = ""

        # -------------------------
        # Build Prompt with Context
        # -------------------------
        system_prompt = build_execution_prompt(effective_mode)

        if rag_context:
            system_prompt += f"\n\nREFERENCE MATERIAL:\n{rag_context}\n\nUse reference material only to support risk detection. Do not treat it as authoritative."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        complete_response = response_generator.generate_response(messages, settings.MODEL_FAST)
        complete_response = normalize_issue_severity(complete_response)
        complete_response = normalize_issue_output(complete_response)

        validation_context = ValidationContext(
            user_input=text,
            session_mode=effective_mode,
            is_creator_question=False
            )

        validation_result = validation_engine.validate_response(
            complete_response,
            validation_context
            )

        if not validation_result.is_valid:
            refusal_message = validation_result.refusal_message or validation_engine.get_refusal_message(
                validation_result.violation_type,
                validation_result.violation_reason
            )
            return StreamingResponse(
            response_generator.stream_to_user(refusal_message),
            media_type="text/plain"
            )

        session["last_report"] = complete_response

        return StreamingResponse(
            response_generator.stream_to_user(complete_response),
            media_type="text/plain"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle any unexpected file processing errors
        logger.error("Unexpected file processing error. session_id=%s filename=%s error=%s", session_id, file.filename, e)
        raise HTTPException(500, f"File processing error: {str(e)}")

@app.post("/reset")
def reset_session(session_id: str = Form(...)):
    if session_id not in sessions.sessions:
        raise HTTPException(400, "Invalid session_id")

    sessions.sessions[session_id] = {
        "history": [],
        "mode": "AUDIT",
        "created_at": time.time()
    }

    return {"status": "reset"}
