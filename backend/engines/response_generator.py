from backend.services.ollama_service import OllamaService
from backend.logger import logger


class ResponseGenerator:
    """Handles single-pass model generation with streaming collection."""

    def __init__(self):
        self.ollama_service = OllamaService()

    def generate_response(self, messages: list, model: str, mode: str = "AUDIT") -> tuple[str, bool]:
        """Generate complete response from model in single pass.

        Args:
            messages: List of message dictionaries for the model
            model: Model name to use for generation

        Returns:
            Tuple of (complete response string, fallback_used bool)

        Raises:
            HTTPException: If model communication fails
        """
        response_text, fallback_used = self.ollama_service.generate_response(messages, model, mode)
        logger.info("[FallbackTrace] stage=response_generator_handoff fallback_used=%s", fallback_used)
        return response_text, fallback_used

    def stream_to_user(self, content: str):
        yield content
