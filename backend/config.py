from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MODEL_FAST: str = "qwen2.5:3b-instruct"
    MODEL_FALLBACK: str = "qwen2.5:7b-instruct"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    MAX_FILE_SIZE: int = 20000

    class Config:
        env_file = ".env"


settings = Settings()
