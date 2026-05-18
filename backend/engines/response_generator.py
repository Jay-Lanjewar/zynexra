from backend.services.ollama_service import OllamaService


class ResponseGenerator:
    """Handles single-pass model generation with streaming collection."""

    def __init__(self):
        self.ollama_service = OllamaService()

    def generate_response(self, messages: list, model: str, mode: str = "AUDIT") -> str:
        """Generate complete response from model in single pass.

        Args:
            messages: List of message dictionaries for the model
            model: Model name to use for generation

        Returns:
            Complete response string from the model

        Raises:
            HTTPException: If model communication fails
        """
        return self.ollama_service.generate_response(messages, model, mode)

    def stream_to_user(self, content: str):
        yield content
