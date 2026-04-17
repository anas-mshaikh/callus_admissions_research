# src/callus_research/config.py

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Callus Admissions Research"
    app_env: str = "dev"
    log_level: str = "INFO"

    data_dir: Path = Path("./data")
    default_timeout: int = 30
    user_agent: str = "callus-research-bot/0.1"

    llm_provider: str = "openai"  # openai | gemini | hf_inference | hf_space
    llm_model: str = "gpt-4.1"

    openai_api_key: str | None = None
    google_api_key: str | None = None
    hf_token: str | None = None

    hf_model_id: str | None = None
    hf_space_id: str | None = None
    hf_space_api_name: str = "/predict"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
