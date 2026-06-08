from typing import Any, Dict, List, Optional, Tuple

from backend.services.ollama_service import OllamaService
from backend.logger import logger


class ResponseGenerator:
    """Handles single-pass model generation with streaming collection."""

    def __init__(self):
        self.ollama_service = OllamaService()

    def generate_response(
        self,
        messages: list,
        model: str,
        mode: str = "AUDIT",
        document_meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, bool, Dict[str, Any]]:
        """Generate complete response from model in single pass.

        Args:
            messages: List of message dictionaries for the model
            model: Model name to use for generation
            mode: Generation profile name
            document_meta: Optional document context for analysis_metadata
                (e.g. {"pages_seen": 12}). When None, pages_seen is None.

        Returns:
            Tuple of (complete response string, fallback_used bool,
            analysis_metadata dict)

        Raises:
            HTTPException: If model communication fails
        """
        response_text, fallback_used, analysis_metadata = self.ollama_service.generate_response(
            messages, model, mode, document_meta
        )
        logger.info("[FallbackTrace] stage=response_generator_handoff fallback_used=%s", fallback_used)
        return response_text, fallback_used, analysis_metadata

    def stream_to_user(self, content: str):
        yield content
