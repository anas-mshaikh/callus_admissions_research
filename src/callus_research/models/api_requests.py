from pydantic import BaseModel

from callus_research.models.source_bundle import ResearchIntent, ResearchTarget


class RuntimeOptions(BaseModel):
    llm_provider: str | None = None
    llm_model: str | None = None
    discovery_provider: str | None = None
    discovery_model: str | None = None
    hf_token: str | None = None
    google_search_api_key: str | None = None
    google_search_engine_id: str | None = None
    vertex_search_project_id: str | None = None
    vertex_search_location: str | None = None
    vertex_search_data_store_id: str | None = None
    vertex_search_serving_config_id: str | None = None
    vertex_search_credentials_path: str | None = None


class ResearchRunIntentRequest(BaseModel):
    target: ResearchIntent
    runtime: RuntimeOptions | None = None


class ResearchRunTargetRequest(BaseModel):
    target: ResearchTarget
    runtime: RuntimeOptions | None = None
