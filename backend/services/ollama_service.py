from typing import Any, Dict, Optional
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
        # Keep AUDIT identical to the previous shared config for regression stability.
        "num_predict": 512,
        "temperature": 0.1,
        "num_ctx": 3072,
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


class OllamaService:
    def generate_response(self, messages: list, model: str, mode: str = "AUDIT") -> tuple[str, bool]:
        try:
            result = self._generate_with_model(messages, model, mode), False
            logger.info("[FallbackTrace] stage=ollama_service_success fallback_used=False")
            return result
        except HTTPException as e:
            if self._should_fallback(e):
                logger.warning("Model fallback activated. Switching to %s", settings.MODEL_FALLBACK)
                result = self._generate_with_model(messages, settings.MODEL_FALLBACK, mode), True
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

    def _generate_with_model(self, messages: list, model: str, mode: str) -> str:
        """Generate complete response from a specific model in single pass."""
        inference_start = None
        profile_name, generation_options = self._get_generation_options(mode)
        try:
            # Single model call - no retries
            inference_start = time.time()
            logger.info("[Inference] Using generation profile -> %s", profile_name)
            stream = ollama_client.chat(
                model=model,
                messages=messages,
                stream=True,
                options=generation_options
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

            # Ensure we got some response
            if not buffer.strip():
                raise HTTPException(500, "Model communication error: Empty response received")

            if self._was_truncated(final_chunk, generation_options):
                logger.warning("[Inference] Response hit generation budget -> profile=%s options=%s", profile_name, generation_options)
                buffer = f"{buffer.rstrip()}\n\n...response truncated"

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
        finally:
            if inference_start is not None:
                inference_duration = log_timing("Ollama inference", inference_start)
                logger.info(
                    "[Timing] Ollama inference comparison -> before_options=%s after_options=%s after_duration=%.2fs",
                    PREVIOUS_GENERATION_OPTIONS,
                    generation_options,
                    inference_duration
                )
