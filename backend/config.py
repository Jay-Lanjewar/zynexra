from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MODEL_FAST: str = "qwen2.5:3b-instruct"
    MODEL_FALLBACK: str = "qwen2.5:7b-instruct"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Raw file size limits per type (in bytes)
    MAX_PDF_SIZE: int = 25 * 1024 * 1024       # 25 MB
    MAX_DOC_SIZE: int = 15 * 1024 * 1024       # 15 MB
    MAX_TXT_SIZE: int = 2 * 1024 * 1024        # 2 MB

    # Extracted text character limit
    MAX_TEXT_LENGTH: int = 500000

    class Config:
        env_file = ".env"


settings = Settings()
