from typing import Any, Dict, List, Optional, Tuple
import time

from fastapi import HTTPException
import ollama

from backend.config import settings
from backend.logger import logger
from backend.utils.timing import log_timing

ollama_client = ollama.Client(host="http://localhost:11434")
PREVIOUS_GENERATION_OPTIONS = {
    "temperature": 0,
    "num_ctx": 4096,
}
GENERATION_PROFILES = {
    "AUDIT": {
        # Benchmarked 2026-06-07: Phase 1 audit responses averaged ~600 tokens
        # with p95 ~870 tokens, and num_predict=192 caused a 100% retry rate.
        # 768 avoids most retries while keeping 1024 retry fallback for outliers.
        "num_predict": 768,
        "temperature": 0.1,
        "num_ctx": 2048,
    },
    "REDACTION": {
        "num_predict": 768,
        "temperature": 0,
        "num_ctx": 3072,
    },
    "ADVISORY": {
        "num_predict": 1536,
        "temperature": 0.3,
        "num_ctx": 4096,
    },
}
MODEL_NAME = settings.MODEL_FAST

AnalysisMetadata = Dict[str, Any]


class OllamaService:
    def generate_response(
        self,
        messages: list,
        model: str,
        mode: str = "AUDIT",
        document_meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, bool, AnalysisMetadata]:
        """Run inference. Returns (response_text, fallback_used, analysis_metadata).

        analysis_metadata is always a dict; if no document_meta was provided
        (e.g. text-only /ask endpoint), it is returned as {}.
        """
        try:
            result = self._generate_with_model(messages, model, mode, document_meta) + (False,)
            logger.info("[FallbackTrace] stage=ollama_service_success fallback_used=False")
            return result
        except HTTPException as e:
            if self._should_fallback(e):
                logger.warning("Model fallback activated. Switching to %s", settings.MODEL_FALLBACK)
                result = self._generate_with_model(messages, settings.MODEL_FALLBACK, mode, document_meta) + (True,)
                logger.warning("[FallbackTrace] stage=ollama_service_fallback fallback_used=True")
                return result
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

    def _get_generation_options(self, mode: str) -> tuple[str, Dict[str, Any]]:
        profile_name = str(mode or "AUDIT").upper()
        if profile_name not in GENERATION_PROFILES:
            profile_name = "AUDIT"
        return profile_name, GENERATION_PROFILES[profile_name]

    def _was_truncated(self, final_chunk: Optional[Dict[str, Any]], options: Dict[str, Any]) -> bool:
        if not final_chunk:
            return False

        done_reason = str(final_chunk.get("done_reason") or final_chunk.get("reason") or "").lower()
        if done_reason in {"length", "num_predict", "max_tokens"}:
            return True

        eval_count = final_chunk.get("eval_count")
        num_predict = options.get("num_predict")
        return isinstance(eval_count, int) and isinstance(num_predict, int) and eval_count >= num_predict

    def _estimate_prompt_tokens(self, messages: list) -> int:
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return max(1, total_chars // 4)

    def _run_inference(self, messages: list, model: str, options: dict) -> tuple[str, Optional[Dict[str, Any]]]:
        stream = ollama_client.chat(
            model=model,
            messages=messages,
            stream=True,
            options=options
        )
        buffer = ""
        final_chunk: Optional[Dict[str, Any]] = None
        for chunk in stream:
            if chunk is None:
                raise HTTPException(500, "Model communication error: Received null chunk")
            final_chunk = chunk
            content = chunk.get("message", {}).get("content", "")
            if content:
                buffer += content
        return buffer, final_chunk

    def _generate_with_model(
        self,
        messages: list,
        model: str,
        mode: str,
        document_meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, AnalysisMetadata]:
        """Generate complete response from a specific model in single pass.

        Returns (response_text, analysis_metadata). analysis_metadata always
        contains a stable shape:

            {
                "was_truncated": bool,
                "kept_chars": int,
                "dropped_chars": int,
                "context_utilization_pct": float,
                "pages_seen": int | None,
            }

        When document_meta is None (e.g. text-only /ask endpoint), pages_seen
        is None and the *_chars fields reflect the user-message length sent
        to the model (which has no separate document-source notion).
        """
        inference_start = None
        profile_name, generation_options = self._get_generation_options(mode)
        if profile_name == "AUDIT":
            logger.info(
                "[InferenceOptimization] num_predict_reduced=%s",
                generation_options.get("num_predict")
            )

        MAX_CONTEXT_WINDOW = 8192
        estimated_tokens = self._estimate_prompt_tokens(messages)
        current_ctx = generation_options.get("num_ctx", 2048)

        # Track the user-message length before any truncation. This becomes
        # the "kept_chars" baseline; if overflow truncation fires, the actual
        # post-truncation length is used instead.
        original_user_chars = 0
        for msg in messages:
            if msg.get("role") == "user":
                original_user_chars = len(str(msg.get("content", "")))
                break

        was_truncated = False
        post_truncation_user_chars = original_user_chars

        if estimated_tokens > MAX_CONTEXT_WINDOW:
            overflow_tokens = estimated_tokens - MAX_CONTEXT_WINDOW
            overflow_chars = overflow_tokens * 4
            messages = list(messages)
            for i, msg in enumerate(messages):
                if msg.get("role") == "user":
                    content = str(msg.get("content", ""))
                    keep_chars = max(len(content) - overflow_chars, 0)
                    messages[i] = {**msg, "content": content[:keep_chars]}
                    post_truncation_user_chars = keep_chars
                    if keep_chars < len(content):
                        was_truncated = True
                    logger.warning(
                        "[ContextOverflow] estimated_prompt_tokens=%d max_ctx=%d "
                        "overflow_tokens=%d overflow_chars=%d "
                        "document_truncated=%d->%d_chars "
                        "system_prompt_preserved=True",
                        estimated_tokens, MAX_CONTEXT_WINDOW,
                        overflow_tokens, overflow_chars,
                        len(content), keep_chars
                    )
                    break
            estimated_tokens = self._estimate_prompt_tokens(messages)
            generation_options = dict(generation_options)
            generation_options["num_ctx"] = MAX_CONTEXT_WINDOW
            ctx_util_pct = round((estimated_tokens / MAX_CONTEXT_WINDOW) * 100, 1)
            logger.info(
                "[ContextMetrics] after_overflow_truncation estimated_prompt_tokens=%d "
                "context_utilization=%.1f%%",
                estimated_tokens, ctx_util_pct
            )
        elif estimated_tokens > current_ctx:
            ctx_util_pct = round((estimated_tokens / current_ctx) * 100, 1)
            logger.info(
                "[ContextMetrics] estimated_prompt_tokens=%d num_ctx=%d context_utilization=%.1f%% exceeds_ctx=True",
                estimated_tokens, current_ctx, ctx_util_pct
            )
            target_ctx = min(estimated_tokens + 512, MAX_CONTEXT_WINDOW)
            logger.warning(
                "[ContextWarning] Prompt exceeds context window: estimated_tokens=%d num_ctx=%d->%d",
                estimated_tokens, current_ctx, target_ctx
            )
            generation_options = dict(generation_options)
            generation_options["num_ctx"] = target_ctx
        else:
            ctx_util_pct = round((estimated_tokens / current_ctx) * 100, 1)
            logger.info(
                "[ContextMetrics] estimated_prompt_tokens=%d num_ctx=%d context_utilization=%.1f%% exceeds_ctx=False",
                estimated_tokens, current_ctx, ctx_util_pct
            )

        try:
            inference_start = time.time()
            logger.info("[Inference] Using generation profile -> %s options=%s", profile_name, generation_options)
            buffer, final_chunk = self._run_inference(messages, model, generation_options)

            if not buffer.strip():
                raise HTTPException(500, "Model communication error: Empty response received")

            if self._was_truncated(final_chunk, generation_options):
                logger.warning("[Inference] Response hit generation budget -> profile=%s options=%s", profile_name, generation_options)
                retry_options = dict(generation_options)
                retry_options["num_predict"] = 1024
                logger.warning(
                    "[InferenceRetry] Retrying with larger generation budget -> num_predict=%s",
                    retry_options["num_predict"]
                )
                retry_buffer, retry_final_chunk = self._run_inference(messages, model, retry_options)
                if retry_buffer.strip():
                    if not self._was_truncated(retry_final_chunk, retry_options):
                        buffer = retry_buffer
                        generation_options = retry_options
                    else:
                        buffer = f"{retry_buffer.rstrip()}\n\n...response truncated"

            # Build analysis_metadata. dropped_chars is measured against the
            # original user-message length, not the document-source length
            # (which is not separately tracked here for the /ask path).
            pages_seen: Optional[int] = None
            if document_meta and "pages_seen" in document_meta:
                pages_seen = document_meta.get("pages_seen")
            analysis_metadata: AnalysisMetadata = {
                "was_truncated": was_truncated,
                "kept_chars": post_truncation_user_chars,
                "dropped_chars": max(0, original_user_chars - post_truncation_user_chars),
                "context_utilization_pct": ctx_util_pct,
                "pages_seen": pages_seen,
            }
            logger.info(
                "[AnalysisMetadata] was_truncated=%s kept_chars=%d dropped_chars=%d "
                "context_utilization_pct=%.1f pages_seen=%s",
                analysis_metadata["was_truncated"],
                analysis_metadata["kept_chars"],
                analysis_metadata["dropped_chars"],
                analysis_metadata["context_utilization_pct"],
                analysis_metadata["pages_seen"],
            )
            return buffer, analysis_metadata

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
        finally:
            if inference_start is not None:
                inference_duration = log_timing("Ollama inference", inference_start)
                logger.info(
                    "[Timing] Ollama inference comparison -> before_options=%s after_options=%s after_duration=%.2fs",
                    PREVIOUS_GENERATION_OPTIONS,
                    generation_options,
                    inference_duration
                )
