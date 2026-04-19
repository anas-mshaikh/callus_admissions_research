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
    discovery_provider: str = "adk_google_search"
    discovery_model: str = "gemini-2.0-flash"

    openai_api_key: str | None = None
    google_api_key: str | None = None
    google_search_api_key: str | None = None
    google_search_engine_id: str | None = None
    vertex_search_project_id: str | None = None
    vertex_search_location: str = "global"
    vertex_search_data_store_id: str | None = None
    vertex_search_serving_config_id: str = "default_config"
    vertex_search_credentials_path: str | None = None
    hf_token: str | None = None

    hf_model_id: str | None = None
    hf_space_id: str | None = None
    hf_space_api_name: str = "/predict"

    source_discovery_prompt_path: Path = Path(
        "src/callus_research/prompts/source_discovery.txt"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def source_discovery_prompt(self) -> str:
        return self.source_discovery_prompt_path.read_text(encoding="utf-8")


settings = Settings()
