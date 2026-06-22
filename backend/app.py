from fastapi import FastAPI, HTTPException, Query as QueryParam
from fastapi.responses import JSONResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, Any, List
import time
from fastapi import UploadFile, File, Form
from backend.config import settings
from backend.services.db_service import db_service
from backend.engines.normalization_engine import (
    build_mode_json_payload,
    is_json_response_mode,
    log_regression_debug,
    normalize_audit_response,
    parse_audit_issues,
    should_debug_regression_case,
)
from backend.engines.confidence_engine import audit_scorer, advisory_scorer
from backend.engines.redaction_engine import RedactionEngine, parse_redaction_options
from backend.engines.response_generator import ResponseGenerator
from backend.engines.validation_engine import ValidationContext, ValidationEngine, ValidationResult
from backend.engines.response_schemas import (
    build_audit_response,
    build_redaction_response,
    build_advisory_response,
    build_policy_response,
    build_non_legal_response,
    classify_non_legal_content,
    build_refusal_response,
    convert_history_record_to_response,
    get_legacy_text_for_export,
    validate_response,
    SCHEMA_VERSION,
)
from backend.engines.policy_detection_engine import (
    detect_policy_document,
    PolicyDetection,
)
from backend.engines.legal_domain_engine import (
    compute_document_domain_confidence,
    DocumentDomain,
)
from backend.logger import logger
from backend.prompts import build_execution_prompt
from backend.services.pdf_service import extract_text_from_pdf, extract_text_from_pdf_with_stats
from backend.services.docx_service import extract_text_from_docx, extract_text_from_docx_with_stats
from backend.utils.timing import log_timing
from backend.verifiers import run_verifiers

MODEL_NAME = settings.MODEL_FAST
# =====================
# Data Models
# =====================

# =====================
# App
# =====================
app = FastAPI(title="Zynexra API")

FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("[CORS] Enabled frontend origins -> %s", FRONTEND_ORIGINS)
logger.info(f"Using inference model: {MODEL_NAME}")

CREATOR_STATEMENT = (
    "I was created by Jay Lanjewar."
)


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
redaction_engine = RedactionEngine()


# =====================
# Additional Models
# =====================
class Query(BaseModel):
    question: str
    session_id: str
    mode: Optional[str] = None
    task_anchor: Optional[str] = None
    response_format: Optional[str] = None
    redact_emails: Optional[bool] = None
    redact_phones: Optional[bool] = None
    redact_names: Optional[bool] = None
    redact_addresses: Optional[bool] = None
    redact_companies: Optional[bool] = None


class SetModeRequest(BaseModel):
    session_id: str
    mode: str


def is_creator_question(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in [
        "who made you",
        "who created you",
        "who built you",
        "who is your creator",
    ])

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
def export_report(session_id: str = Form(...), response_format: Optional[str] = Form(None)):
    session = sessions.get(session_id)

    report_text = session.get("last_report")
    structured_response = session.get("last_structured_response")

    if not report_text and not structured_response:
        raise HTTPException(400, "No report available to export.")

    if response_format and response_format.lower() == "json":
        if structured_response:
            logger.info("[Schema] Export returning validated JSON response")
            return JSONResponse(structured_response)

        logger.warning("[Schema] No structured response available for export, building from raw text")
        mode = session.get("mode", "AUDIT")
        if mode == "AUDIT":
            issues = parse_audit_issues(report_text or "")
            structured = build_audit_response(
                complete_response=report_text or "",
                model=MODEL_NAME,
                issues=[issue.to_dict() for issue in issues] if issues else [],
                structured_parse_failed=not issues
            )
        elif mode == "REDACTION":
            structured = build_redaction_response(
                model=MODEL_NAME,
                original_text=report_text or "",
                redacted_text=report_text or ""
            )
        else:
            structured = build_advisory_response(
                complete_response=report_text or "",
                model=MODEL_NAME
            )
        validate_response(structured, mode)
        return JSONResponse(structured)

    return Response(
        content=report_text or "",
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=zynexra_report.txt"
        }
    )

# =====================
# Endpoint
# =====================
@app.post("/ask")
def ask(q: Query, response_format: Optional[str] = None):
    request_start = time.time()
    log_timing("Request received", request_start)

    if not q.session_id:
        raise HTTPException(422, "session_id required")

    logger.info("Incoming /ask request. session_id=%s", q.session_id)

    session = sessions.get(q.session_id)
    text = q.question.strip()
    json_response_mode = is_json_response_mode(response_format or q.response_format)
    if json_response_mode:
        logger.info("[API] JSON response mode enabled")

    # -----------------
    # Creator identity (backend enforced)
    # -----------------
    if is_creator_question(text):
        log_timing("Total request", request_start)
        if json_response_mode:
            return JSONResponse(build_advisory_response(
                complete_response=CREATOR_STATEMENT,
                model=MODEL_NAME
            ))
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
        redaction_start = time.time()
        redaction_result = redaction_engine.redact(
            text,
            parse_redaction_options({
                "redact_emails": q.redact_emails,
                "redact_phones": q.redact_phones,
                "redact_names": q.redact_names,
                "redact_addresses": q.redact_addresses,
                "redact_companies": q.redact_companies,
            }),
        )
        complete_response = redaction_result.redacted_text
        log_timing("Redaction", redaction_start)

        validation_context = ValidationContext(
            user_input=text,
            session_mode=session["mode"],
            is_creator_question=is_creator_question(text)
        )
        validation_start = time.time()
        validation_result = validation_engine.validate_response(complete_response, validation_context)
        log_timing("Validation", validation_start)
        log_timing("Total request", request_start)

        if validation_result.is_valid:
            session["last_report"] = complete_response
            structured = redaction_result.to_payload(MODEL_NAME)
            session["last_structured_response"] = structured
            if sessions.should_update_history(validation_result):
                sessions.add_valid_exchange(q.session_id, text, complete_response)

            # Persist redaction to database
            try:
                if db_service.available:
                    redaction_types = ",".join(type(e).__name__ for e in redaction_result.entities) if redaction_result.entities else ""
                    entities_dict = {str(i): e.__dict__ if hasattr(e, '__dict__') else e for i, e in enumerate(redaction_result.entities)}
                    db_service.insert_redaction(
                        filename="text_input",
                        redaction_count=len(redaction_result.entities),
                        entities=entities_dict,
                        redacted_text=complete_response,
                        redaction_types=redaction_types
                    )
            except Exception as e:
                logger.warning(f"Failed to persist redaction: {str(e)}")

            if json_response_mode:
                if not validate_response(structured, "REDACTION"):
                    logger.warning("[Schema] Redaction response validation failed during fresh execution")
                return JSONResponse(structured)
            return StreamingResponse(
                response_generator.stream_to_user(complete_response),
                media_type="text/plain"
            )

        refusal_message = validation_result.refusal_message or validation_engine.get_refusal_message(
            validation_result.violation_type, validation_result.violation_reason
        )
        if json_response_mode:
            return JSONResponse(build_refusal_response(refusal_message, MODEL_NAME, "REDACTION"))
        return StreamingResponse(
            response_generator.stream_to_user(refusal_message),
            media_type="text/plain"
        )

    # -----------------
    # Build prompt
    # -----------------
    prompt_start = time.time()
    system_prompt = build_execution_prompt(session["mode"])

    # Inject task anchor if provided (e.g. for file uploads)
    if q.task_anchor:
        system_prompt = f"{q.task_anchor}\n\n{system_prompt}"

    messages = [{"role": "system", "content": system_prompt}]
    for turn in session["history"]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    messages.append({"role": "user", "content": text})
    log_timing("Prompt build", prompt_start)

    if json_response_mode:
        inference_start = time.time()
        try:
            raw_response, fallback_used, _analysis_metadata = response_generator.generate_response(messages, settings.MODEL_FAST, session["mode"])
            inference_duration_ms = (time.time() - inference_start) * 1000
            logger.info("[Perf] inference_ms=%.0f", inference_duration_ms)
            logger.info("[FallbackTrace] stage=app_json_response_handoff fallback_used=%s", fallback_used)
            issues = parse_audit_issues(raw_response)
            normalization_start = time.time()
            complete_response, normalized_issues = normalize_audit_response(raw_response, session["mode"], parsed_issues=issues, doc_text=text)
            norm_ms = (time.time() - normalization_start) * 1000
            logger.info("[Perf] normalization_ms=%.0f", norm_ms)
            if should_debug_regression_case(q.session_id, q.task_anchor, text):
                log_regression_debug(raw_response, complete_response)
        except HTTPException as http_err:
            raise http_err
        except Exception as e:
            logger.error("Unexpected error during /ask generation. session_id=%s error=%s", q.session_id, e)
            raise HTTPException(500, f"Unexpected error during generation: {str(e)}")

        try:
            validation_context = ValidationContext(
                user_input=text,
                session_mode=session["mode"],
                is_creator_question=is_creator_question(text)
            )
            validation_start = time.time()
            validation_result = validation_engine.validate_response(complete_response, validation_context)
            validation_ms = (time.time() - validation_start) * 1000
            log_timing("Validation", validation_start)
        except Exception as e:
            logger.error("Validation error during /ask. session_id=%s error=%s", q.session_id, e)
            raise HTTPException(500, f"Validation error: {str(e)}")

        total_ms = (time.time() - request_start) * 1000
        log_timing("Total request", request_start)
        logger.info("[Perf] total_ms=%.0f", total_ms)

        if validation_result.is_valid:
            session["last_report"] = complete_response
            logger.info("[FallbackTrace] stage=app_build_audit_payload fallback_used=%s", fallback_used)
            structured = build_mode_json_payload(complete_response, MODEL_NAME, session["mode"], user_query=text, fallback_used=fallback_used, inference_duration_ms=inference_duration_ms, parsed_issues=normalized_issues)
            if fallback_used:
                structured["fallback_used"] = True
                if "metadata" in structured:
                    structured["metadata"]["fallback_used"] = True
            # ---- Verifier Layer ----
            if session["mode"] == "AUDIT" and structured.get("response_type") == "audit":
                try:
                    verifier_issues = run_verifiers(text, structured.get("issues", []))
                    if verifier_issues:
                        structured["issues"].extend(verifier_issues)
                        structured["issue_count"] = len(structured["issues"])
                        logger.info("[Verifier] Appended %d verifier issue(s)", len(verifier_issues))
                except Exception as e:
                    logger.error("[Verifier] Failed: %s", e)
            session["last_structured_response"] = structured
            if not validate_response(structured, session["mode"]):
                logger.warning(f"[Schema] {session['mode']} response validation failed during fresh execution")
            if sessions.should_update_history(validation_result):
                sessions.add_valid_exchange(q.session_id, text, complete_response)

            # Persist to database based on mode (reuse structured payload - no duplicate rebuild)
            try:
                if db_service.available:
                    if session["mode"] == "ADVISORY":
                        messages = [{"role": "user", "content": turn["user"]} for turn in session["history"]]
                        messages.extend([{"role": "assistant", "content": turn["assistant"]} for turn in session["history"]])
                        db_service.insert_advisory(
                            session_id=q.session_id,
                            messages=messages,
                            title=f"Advisory Session {q.session_id[:8]}"
                        )
                        logger.debug(f"[History] Saving record -> mode={session['mode']}, session_id={q.session_id}")
                    else:
                        issue_count = structured.get("issue_count", 0)
                        issues = structured.get("issues", [])
                        record_id = db_service.insert_audit(
                            filename="text_input",
                            issue_count=issue_count,
                            issues=issues,
                            raw_response=complete_response,
                            mode=session["mode"],
                            severity_level="HIGH" if issue_count > 0 else "LOW"
                        )
                        logger.debug(f"[History] Saving record -> mode={session['mode']}, id={record_id}")
            except Exception as e:
                logger.warning(f"Failed to persist history: {str(e)}")

            return JSONResponse(structured)

        refusal_message = validation_result.refusal_message or validation_engine.get_refusal_message(
            validation_result.violation_type, validation_result.violation_reason
        )
        return JSONResponse(build_refusal_response(refusal_message, MODEL_NAME, session["mode"]))

    # -----------------
    # Streaming response
    # -----------------
    def generate():
        # Send immediate heartbeat so connection stays open
        yield ""
        # Always try fast model first. ResponseGenerator handles fallback internally.
        try:
            inference_start = time.time()
            raw_response, fallback_used, _analysis_metadata = response_generator.generate_response(messages, settings.MODEL_FAST, session["mode"])
            inference_duration_ms = (time.time() - inference_start) * 1000
            logger.info("[Perf] inference_ms=%.0f", inference_duration_ms)
            logger.info("[FallbackTrace] stage=app_streaming_response_handoff fallback_used=%s", fallback_used)
            issues = parse_audit_issues(raw_response)
            normalization_start = time.time()
            complete_response, normalized_issues = normalize_audit_response(raw_response, session["mode"], parsed_issues=issues, doc_text=text)
            norm_ms = (time.time() - normalization_start) * 1000
            logger.info("[Perf] normalization_ms=%.0f", norm_ms)
            if should_debug_regression_case(q.session_id, q.task_anchor, text):
                log_regression_debug(raw_response, complete_response)
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
            
            validation_start = time.time()
            validation_result = validation_engine.validate_response(complete_response, validation_context)
            log_timing("Validation", validation_start)
        except Exception as e:
            # Handle validation engine failures gracefully
            logger.error("Validation error during /ask. session_id=%s error=%s", q.session_id, e)
            raise HTTPException(500, f"Validation error: {str(e)}")
        
        total_ms = (time.time() - request_start) * 1000
        log_timing("Total request", request_start)
        logger.info("[Perf] total_ms=%.0f", total_ms)
        
        if validation_result.is_valid:
            # Stream the valid response to user
            try:
                for char in response_generator.stream_to_user(complete_response):
                    yield char
                final_response = complete_response
                session["last_report"] = complete_response
                logger.info("[FallbackTrace] stage=app_streaming_build_payload fallback_used=%s", fallback_used)
                structured = build_mode_json_payload(complete_response, MODEL_NAME, session["mode"], user_query=text, fallback_used=fallback_used, inference_duration_ms=inference_duration_ms, parsed_issues=normalized_issues)
                if fallback_used:
                    structured["fallback_used"] = True
                    if "metadata" in structured:
                        structured["metadata"]["fallback_used"] = True
                # ---- Verifier Layer ----
                if session["mode"] == "AUDIT" and structured.get("response_type") == "audit":
                    try:
                        verifier_issues = run_verifiers(text, structured.get("issues", []))
                        if verifier_issues:
                            structured["issues"].extend(verifier_issues)
                            structured["issue_count"] = len(structured["issues"])
                            logger.info("[Verifier] Appended %d verifier issue(s)", len(verifier_issues))
                    except Exception as e:
                        logger.error("[Verifier] Failed: %s", e)
                session["last_structured_response"] = structured
                if not validate_response(structured, session["mode"]):
                    logger.warning(f"[Schema] {session['mode']} response validation failed during streaming")

                # Only store valid responses in conversation history using SessionManager
                if sessions.should_update_history(validation_result):
                    sessions.add_valid_exchange(q.session_id, text, final_response)
                
                # Persist to database based on mode (reuse structured payload - no duplicate rebuild)
                try:
                    if db_service.available:
                        if session["mode"] == "ADVISORY":
                            messages = [{"role": "user", "content": turn["user"]} for turn in session["history"]]
                            messages.extend([{"role": "assistant", "content": turn["assistant"]} for turn in session["history"]])
                            record_id = db_service.insert_advisory(
                                session_id=q.session_id,
                                messages=messages,
                                title=f"Advisory Session {q.session_id[:8]}"
                            )
                            logger.debug(f"[History] Saving record -> mode={session['mode']}, session_id={q.session_id}")
                        elif session["mode"] == "AUDIT":
                            issue_count = structured.get("issue_count", 0)
                            issues = structured.get("issues", [])
                            record_id = db_service.insert_audit(
                                filename="text_input",
                                issue_count=issue_count,
                                issues=issues,
                                raw_response=final_response,
                                mode=session["mode"],
                                severity_level="HIGH" if issue_count > 0 else "LOW"
                            )
                            logger.debug(f"[History] Saving record -> mode={session['mode']}, id={record_id}")
                        elif session["mode"] == "REDACTION":
                            db_service.insert_redaction(
                                filename="text_input",
                                redaction_count=0,
                                entities={},
                                redacted_text=final_response
                            )
                except Exception as e:
                    logger.warning(f"Failed to persist response: {str(e)}")
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

@app.post("/ask_file")
def ask_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    mode: Optional[str] = Form(None),
    response_format: Optional[str] = Form(None),
    redact_emails: Optional[bool] = Form(None),
    redact_phones: Optional[bool] = Form(None),
    redact_names: Optional[bool] = Form(None),
    redact_addresses: Optional[bool] = Form(None),
    redact_companies: Optional[bool] = Form(None)
):
    request_start = time.time()
    log_timing("Request received", request_start)
    json_response_mode = is_json_response_mode(response_format)
    if json_response_mode:
        logger.info("[API] JSON response mode enabled")

    # ---- VALIDATION ----
    try:
        session = sessions.get(session_id)

        filename = file.filename.lower() if file.filename else ""
        logger.info("Uploaded file received. session_id=%s filename=%s", session_id, filename)
        
        if not filename.endswith((".txt", ".pdf", ".docx")):
            raise HTTPException(400, "Only .txt, .pdf, and .docx files supported")

        logger.info("Starting file processing. session_id=%s filename=%s", session_id, filename)
        file_read_start = time.time()
        content = file.file.read()
        log_timing("File read", file_read_start)
        if not content:
            raise HTTPException(400, "Empty file")
            
        file.file.close()

        # Check raw file size against per-type limits before extraction
        if filename.endswith(".pdf") and len(content) > settings.MAX_PDF_SIZE:
            raise HTTPException(400, "File exceeds maximum size. PDF files must be under 25MB.")
        if filename.endswith(".docx") and len(content) > settings.MAX_DOC_SIZE:
            raise HTTPException(400, "File exceeds maximum size. DOCX files must be under 15MB.")
        if filename.endswith(".txt") and len(content) > settings.MAX_TXT_SIZE:
            raise HTTPException(400, "File exceeds maximum size. TXT files must be under 2MB.")

        extraction_start = time.time()
        pages_seen: Optional[int] = None
        if filename.endswith(".pdf"):
            text, pages_seen = extract_text_from_pdf_with_stats(content)
        elif filename.endswith(".docx"):
            text, pages_seen = extract_text_from_docx_with_stats(content)
        else:
            # Default to .txt processing
            try:
                text = content.decode("utf-8", errors="ignore")
            except Exception as e:
                logger.error("File encoding error. session_id=%s filename=%s error=%s", session_id, filename, e)
                raise HTTPException(400, f"File encoding error: {str(e)}")
        log_timing("File extraction", extraction_start)

        if len(text) > settings.MAX_TEXT_LENGTH:
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
            redaction_start = time.time()
            redaction_result = redaction_engine.redact(
                text,
                parse_redaction_options({
                    "redact_emails": redact_emails,
                    "redact_phones": redact_phones,
                    "redact_names": redact_names,
                    "redact_addresses": redact_addresses,
                    "redact_companies": redact_companies,
                }),
            )
            complete_response = redaction_result.redacted_text
            log_timing("Redaction", redaction_start)

            validation_context = ValidationContext(
                user_input=text,
                session_mode=effective_mode,
                is_creator_question=False
            )
            validation_start = time.time()
            validation_result = validation_engine.validate_response(
                complete_response,
                validation_context
            )
            log_timing("Validation", validation_start)
            log_timing("Total request", request_start)

            if not validation_result.is_valid:
                refusal_message = validation_result.refusal_message or validation_engine.get_refusal_message(
                    validation_result.violation_type,
                    validation_result.violation_reason
                )
                if json_response_mode:
                    return JSONResponse(build_refusal_response(refusal_message, MODEL_NAME, "REDACTION"))
                return StreamingResponse(
                    response_generator.stream_to_user(refusal_message),
                    media_type="text/plain"
                )

            session["last_report"] = complete_response
            if json_response_mode:
                structured = redaction_result.to_payload(MODEL_NAME)
                session["last_structured_response"] = structured
                # Persist redaction to database
                try:
                    if db_service.available:
                        redaction_types = ",".join(type(e).__name__ for e in redaction_result.entities) if redaction_result.entities else ""
                        entities_dict = {str(i): e.__dict__ if hasattr(e, '__dict__') else e for i, e in enumerate(redaction_result.entities)}
                        db_service.insert_redaction(
                            filename=filename or "file_upload",
                            redaction_count=len(redaction_result.entities),
                            entities=entities_dict,
                            redacted_text=complete_response,
                            redaction_types=redaction_types
                        )
                except Exception as e:
                    logger.warning(f"Failed to persist redaction: {str(e)}")

                if not validate_response(structured, "REDACTION"):
                    logger.warning("[Schema] Redaction response validation failed in ask_file")
                return JSONResponse(structured)
            return StreamingResponse(
                response_generator.stream_to_user(complete_response),
                media_type="text/plain"
            )
         
        # -------------------------
        # Policy/Procedure Document Detection
        # -------------------------
        policy_detection_start = time.time()
        policy_result = detect_policy_document(text)
        if policy_result.detection == PolicyDetection.POLICY:
            log_timing("Policy detection", policy_detection_start)
            logger.warning(
                "[PolicyDetection] POLICY DOCUMENT DETECTED — short-circuiting LLM pipeline. "
                "type=%s confidence=%.4f", policy_result.policy_type, policy_result.confidence,
            )
            policy_response = build_policy_response(
                model=MODEL_NAME,
                policy_type=policy_result.policy_type,
                policy_explanation=policy_result.explanation,
                policy_confidence=policy_result.confidence,
                metadata={
                    "model_name": MODEL_NAME,
                    "policy_keyword_score": round(policy_result.policy_keyword_score, 4),
                    "contractual_signal_score": round(policy_result.contractual_signal_score, 4),
                    "policy_keywords": policy_result.matched_policy_keywords,
                },
            )
            session["last_report"] = f"[POLICY NOTICE] {policy_result.policy_type}: {policy_result.explanation}"
            session["last_structured_response"] = policy_response

            if json_response_mode:
                return JSONResponse(policy_response)

            return StreamingResponse(
                response_generator.stream_to_user(
                    f"[POLICY NOTICE]\n\nThis document has been identified as a policy or procedure document, "
                    f"not a contractual agreement.\n\nClassification: {policy_result.policy_type}\n\n"
                    f"{policy_result.explanation}\n\n"
                    f"Policy documents are not processed through the legal-risk audit pipeline."
                ),
                media_type="text/plain",
            )
        log_timing("Policy detection", policy_detection_start)
        logger.info(
            "[PolicyDetection] No policy detected: detection=%s confidence=%.4f",
            policy_result.detection.value, policy_result.confidence,
        )

        # -------------------------
        # Non-Legal Document Detection
        # -------------------------
        non_legal_start = time.time()
        domain_result = compute_document_domain_confidence(text)
        domain_is_non_legal = domain_result.domain == DocumentDomain.NON_LEGAL
        if domain_is_non_legal:
            log_timing("Non-legal detection", non_legal_start)
            content_type, content_explanation, _ = classify_non_legal_content(text)
            logger.warning(
                "[NonLegalDetection] NON-LEGAL DOCUMENT DETECTED — short-circuiting LLM pipeline. "
                "type=%s domain_confidence=%.4f legal_keyword_ratio=%.4f structure_score=%.4f",
                content_type, domain_result.confidence,
                domain_result.legal_keyword_ratio, domain_result.structure_score,
            )
            non_legal_response = build_non_legal_response(
                model=MODEL_NAME,
                content_type=content_type,
                content_explanation=content_explanation,
                domain_confidence=domain_result.confidence,
                legal_keyword_ratio=domain_result.legal_keyword_ratio,
                structure_score=domain_result.structure_score,
                metadata={
                    "model_name": MODEL_NAME,
                    "domain": domain_result.domain.value,
                    "legal_signal": round(domain_result.factors.get("legal_signal", 0), 4),
                    "non_legal_penalty": round(domain_result.factors.get("non_legal_penalty", 0), 4),
                },
            )
            session["last_report"] = f"[NON-LEGAL NOTICE] {content_type}: {content_explanation}"
            session["last_structured_response"] = non_legal_response

            if json_response_mode:
                return JSONResponse(non_legal_response)

            return StreamingResponse(
                response_generator.stream_to_user(
                    f"[NON-LEGAL DOCUMENT NOTICE]\n\n"
                    f"This document does not appear to be a legal contract or agreement.\n\n"
                    f"Classification: {content_type}\n\n"
                    f"{content_explanation}\n\n"
                    f"The legal-risk audit pipeline requires contractual documents with identifiable "
                    f"legal structure, parties, obligations, and binding language. Non-contract "
                    f"content such as educational materials, notes, questions, or general text "
                    f"is not processed through this pipeline."
                ),
                media_type="text/plain",
            )
        log_timing("Non-legal detection", non_legal_start)
        logger.info(
            "[NonLegalDetection] Domain appears legal: domain=%s confidence=%.4f",
            domain_result.domain.value, domain_result.confidence,
        )

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
        prompt_start = time.time()
        system_prompt = build_execution_prompt(effective_mode)

        if rag_context:
            system_prompt += f"\n\nREFERENCE MATERIAL:\n{rag_context}\n\nUse reference material only to support risk detection. Do not treat it as authoritative."

        if effective_mode == "AUDIT":
            user_content = text + "\n\n---\nRespond ONLY with a single JSON object matching the schema in the system instructions. No other text."
        else:
            user_content = text

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        log_timing("Prompt build", prompt_start)

        system_prompt_len = len(system_prompt)
        schema_start = system_prompt.find("OUTPUT FORMAT")
        schema_snippet = system_prompt[schema_start:schema_start + 300] if schema_start >= 0 else "NOT FOUND"
        logger.info("[PromptDebug] effective_mode=%s system_prompt_length=%d user_content_length=%d text_length=%d",
                     effective_mode, system_prompt_len, len(user_content), len(text))
        logger.info("[PromptDebug] schema_instructions_start=%s",
                     "FOUND" if schema_start >= 0 else "MISSING")
        logger.info("[PromptDebug] schema_snippet=%s", schema_snippet)
        logger.info("[PromptDebug] system_prompt=%s", system_prompt)

        inference_start = time.time()

        try:
            raw_response, fallback_used, analysis_metadata = response_generator.generate_response(
                messages,
                settings.MODEL_FAST,
                effective_mode,
                document_meta={"pages_seen": pages_seen},
            )
        except Exception as e:
            logger.exception("MODEL GENERATION FAILED")
            raise HTTPException(500, f"Model generation failed: {str(e)}")
        inference_duration_ms = (time.time() - inference_start) * 1000
        logger.info("[Perf] inference_ms=%.0f", inference_duration_ms)
        logger.info("[FallbackTrace] stage=app_file_upload_handoff fallback_used=%s", fallback_used)
        response_preview = raw_response[:500].replace("\n", "\\n")
        logger.info("[ResponseDebug] raw_response_first_500_chars=%s", response_preview)
        issues = parse_audit_issues(raw_response)
        normalization_start = time.time()
        complete_response, normalized_issues = normalize_audit_response(raw_response, effective_mode, parsed_issues=issues, doc_text=text)
        norm_ms = (time.time() - normalization_start) * 1000
        logger.info("[Perf] normalization_ms=%.0f", norm_ms)
        if should_debug_regression_case(session_id, filename, text):
            log_regression_debug(raw_response, complete_response)

        validation_context = ValidationContext(
            user_input=text,
            session_mode=effective_mode,
            is_creator_question=False
            )

        validation_start = time.time()
        validation_result = validation_engine.validate_response(
            complete_response,
            validation_context
            )
        validation_ms = (time.time() - validation_start) * 1000
        log_timing("Validation", validation_start)
        total_ms = (time.time() - request_start) * 1000
        log_timing("Total request", request_start)
        logger.info("[Perf] total_ms=%.0f", total_ms)

        if not validation_result.is_valid:
            refusal_message = validation_result.refusal_message or validation_engine.get_refusal_message(
                validation_result.violation_type,
                validation_result.violation_reason
            )
            if json_response_mode:
                return JSONResponse(build_refusal_response(refusal_message, MODEL_NAME, effective_mode))
            return StreamingResponse(
            response_generator.stream_to_user(refusal_message),
            media_type="text/plain"
            )

        session["last_report"] = complete_response

        if json_response_mode:
            structured = build_mode_json_payload(complete_response, MODEL_NAME, effective_mode, user_query=text, fallback_used=fallback_used, inference_duration_ms=inference_duration_ms, parsed_issues=normalized_issues, analysis_metadata=analysis_metadata)
            if fallback_used:
                structured["fallback_used"] = True
                if "metadata" in structured:
                    structured["metadata"]["fallback_used"] = True
            # ---- Verifier Layer ----
            if effective_mode == "AUDIT" and structured.get("response_type") == "audit":
                try:
                    verifier_issues = run_verifiers(text, structured.get("issues", []))
                    if verifier_issues:
                        structured["issues"].extend(verifier_issues)
                        structured["issue_count"] = len(structured["issues"])
                        logger.info("[Verifier] Appended %d verifier issue(s)", len(verifier_issues))
                except Exception as e:
                    logger.error("[Verifier] Failed: %s", e)
            session["last_structured_response"] = structured
            # Persist audit to database (reuse structured - no duplicate rebuild)
            try:
                if db_service.available:
                    issue_count = structured.get("issue_count", 0)
                    issues = structured.get("issues", [])
                    db_service.insert_audit(
                        filename=filename or "file_upload",
                        issue_count=issue_count,
                        issues=issues,
                        raw_response=complete_response,
                        mode=effective_mode,
                        severity_level="HIGH" if issue_count > 0 else "LOW"
                    )
            except Exception as e:
                logger.warning(f"Failed to persist audit: {str(e)}")
                raise HTTPException(400, f"Processing failed: {str(e)}")
            return JSONResponse(structured)

        return StreamingResponse(
            response_generator.stream_to_user(complete_response),
            media_type="text/plain"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle any unexpected file processing errors
        logger.exception("Unexpected file processing error. session_id=%s filename=%s error=%s", session_id, file.filename, e)
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


# =====================
# History Endpoints
# =====================
@app.get("/history")
def get_history(
    record_type: str = QueryParam("all", description="Type: audit, redaction, advisory, or all"),
    limit: int = QueryParam(50, ge=1, le=100),
    offset: int = QueryParam(0, ge=0),
    filename: Optional[str] = QueryParam(None),
    mode: Optional[str] = QueryParam(None),
    severity: Optional[str] = QueryParam(None),
    start_date: Optional[str] = QueryParam(None),
    end_date: Optional[str] = QueryParam(None)
) -> Dict[str, Any]:
    """Retrieve history records with optional filtering."""
    if not db_service.available:
        logger.warning("[API] History endpoint accessed but DB unavailable")
        return {
            "success": False,
            "message": "Database not available",
            "records": [],
            "total": 0,
            "schema_version": SCHEMA_VERSION
        }

    logger.info(
        f"[WorkspaceFilter] records_before=0 "
        f"applied_filters=record_type={record_type},mode={mode},severity={severity},"
        f"filename={filename},start_date={start_date},end_date={end_date}"
    )

    results = {
        "success": True,
        "records": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
        "schema_version": SCHEMA_VERSION
    }

    try:
        # Determine which tables to query based on combined record_type and mode filter
        query_audit = False
        query_redaction = False
        query_advisory = False

        if record_type == "all":
            if mode:
                upper_mode = mode.upper()
                if upper_mode == "AUDIT":
                    query_audit = True
                elif upper_mode == "REDACTION":
                    query_audit = True
                    query_redaction = True
                elif upper_mode == "ADVISORY":
                    query_advisory = True
            else:
                query_audit = True
                query_redaction = True
                query_advisory = True
        else:
            if record_type == "audit":
                query_audit = True
            elif record_type == "redaction":
                query_redaction = True
            elif record_type == "advisory":
                query_advisory = True

        if query_audit:
            audits = db_service.get_audit_history(
                limit=limit,
                offset=offset,
                filename=filename,
                mode=mode,
                severity=severity,
                start_date=start_date,
                end_date=end_date
            )
            logger.debug(f"[WorkspaceFilter] audit_history returned {len(audits)} records")
            standardized_audits = []
            for audit in audits:
                standardized_audits.append({
                    "id": audit.get("id"),
                    "filename": audit.get("filename"),
                    "timestamp": audit.get("timestamp"),
                    "mode": audit.get("mode"),
                    "severity": audit.get("severity_level"),
                    "issue_count": audit.get("issue_count"),
                    "record_type": "audit",
                    "response": build_audit_response(
                        complete_response=audit.get("raw_response", ""),
                        model=MODEL_NAME,
                        issues=audit.get("issues", []),
                        structured_parse_failed=not audit.get("issues")
                    )
                })
            results["records"].extend(standardized_audits)

        if query_redaction:
            redactions = db_service.get_redaction_history(
                limit=limit,
                offset=offset,
                filename=filename,
                start_date=start_date,
                end_date=end_date
            )
            logger.debug(f"[WorkspaceFilter] redaction_history returned {len(redactions)} records")
            standardized_redactions = []
            for redaction in redactions:
                entities_list = list(redaction.get("entities", {}).values()) if redaction.get("entities") else []
                standardized_redactions.append({
                    "id": redaction.get("id"),
                    "filename": redaction.get("filename"),
                    "timestamp": redaction.get("timestamp"),
                    "mode": "REDACTION",
                    "severity": None,
                    "redaction_count": redaction.get("redaction_count"),
                    "record_type": "redaction",
                    "response": build_redaction_response(
                        model=MODEL_NAME,
                        original_text=redaction.get("redacted_text", ""),
                        redacted_text=redaction.get("redacted_text", ""),
                        redaction_entities=entities_list,
                        fallback_used=False
                    )
                })
            results["records"].extend(standardized_redactions)

        if query_advisory:
            advisory = db_service.get_advisory_history(limit=limit, offset=offset)
            logger.debug(f"[WorkspaceFilter] advisory_sessions returned {len(advisory)} records")
            standardized_advisory = []
            for adv in advisory:
                messages = adv.get("messages", [])
                advisory_text = ""
                if isinstance(messages, list):
                    advisory_text = "\n".join(
                        f"User: {m.get('user', '')}\nAssistant: {m.get('assistant', '')}"
                        for m in messages if isinstance(m, dict)
                    )
                standardized_advisory.append({
                    "id": adv.get("id"),
                    "session_id": adv.get("session_id"),
                    "title": adv.get("title"),
                    "timestamp": adv.get("timestamp"),
                    "mode": "ADVISORY",
                    "severity": None,
                    "record_type": "advisory",
                    "response": build_advisory_response(
                        complete_response=advisory_text,
                        model=MODEL_NAME
                    )
                })
            results["records"].extend(standardized_advisory)

        results["total"] = len(results["records"])
        logger.info(
            f"[WorkspaceFilter] records_after={results['total']} "
            f"applied_filters=record_type={record_type},mode={mode},severity={severity}"
        )
        logger.debug(f"[API] Retrieved {results['total']} history records (type={record_type}, mode_filter={mode})")
        logger.debug(f"[History] Workspace fetch -> record_type={record_type}, mode_filter={mode}, total={results['total']}")
        return results

    except Exception as e:
        logger.error(f"[API] Error retrieving history: {str(e)}")
        raise HTTPException(500, f"Error retrieving history: {str(e)}")


@app.get("/history/{record_id}")
def get_record_detail(
    record_id: int,
    record_type: str = QueryParam("audit", description="Type: audit, redaction, or advisory")
) -> Dict[str, Any]:
    """Retrieve a specific record by ID."""
    if not db_service.available:
        raise HTTPException(503, "Database not available")

    if record_type not in ["audit", "redaction", "advisory"]:
        raise HTTPException(400, "Invalid record_type. Must be: audit, redaction, or advisory")

    try:
        record = db_service.get_record(record_type, record_id)
        if not record:
            raise HTTPException(404, f"{record_type.capitalize()} record not found")

        standardized_response = convert_history_record_to_response(record, record_type, MODEL_NAME)

        if not validate_response(standardized_response, record_type.upper()):
            logger.warning(f"[Schema] History record validation failed for id={record_id}, type={record_type}")

        logger.debug(f"[API] Retrieved record detail: id={record_id}, type={record_type}")
        return {
            "success": True,
            "record": record,
            "response": standardized_response,
            "schema_version": SCHEMA_VERSION
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error retrieving record: {str(e)}")
        raise HTTPException(500, f"Error retrieving record: {str(e)}")


@app.delete("/history/{record_id}")
def delete_record(
    record_id: int,
    record_type: str = QueryParam("audit", description="Type: audit, redaction, or advisory")
) -> Dict[str, Any]:
    """Delete a record by ID."""
    if not db_service.available:
        raise HTTPException(503, "Database not available")
    
    if record_type not in ["audit", "redaction", "advisory"]:
        raise HTTPException(400, "Invalid record_type. Must be: audit, redaction, or advisory")
    
    try:
        success = db_service.delete_record(record_type, record_id)
        if not success:
            raise HTTPException(404, f"{record_type.capitalize()} record not found")
        
        logger.info(f"[API] Record deleted: id={record_id}, type={record_type}")
        return {
            "success": True,
            "message": f"{record_type.capitalize()} record deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error deleting record: {str(e)}")
        raise HTTPException(500, f"Error deleting record: {str(e)}")


@app.get("/history/stats/summary")
def get_history_summary() -> Dict[str, Any]:
    """Get summary statistics of all history records."""
    if not db_service.available:
        return {
            "success": False,
            "message": "Database not available",
            "stats": {}
        }
    
    try:
        audits = db_service.get_audit_history(limit=1000)
        redactions = db_service.get_redaction_history(limit=1000)
        advisory = db_service.get_advisory_history(limit=1000)
        
        stats = {
            "total_audits": len(audits),
            "total_redactions": len(redactions),
            "total_advisory_sessions": len(advisory),
            "total_issues_found": sum(a.get("issue_count", 0) for a in audits),
            "total_entities_redacted": sum(r.get("redaction_count", 0) for r in redactions)
        }
        
        logger.debug(f"[API] Retrieved history summary: {stats}")
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"[API] Error retrieving summary: {str(e)}")
        return {
            "success": False,
            "message": f"Error retrieving summary: {str(e)}",
            "stats": {}
        }
