from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Callus Admissions Research"
    app_env: str = "dev"
    log_level: str = "INFO"

    data_dir: Path = Path("./data")
    default_timeout: int = 30
    user_agent: str = "callus-research-bot/0.1"

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
