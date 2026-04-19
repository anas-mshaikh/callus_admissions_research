from fastapi import APIRouter, HTTPException

from callus_research.config import settings
from callus_research.models.api_requests import (
    ResearchRunIntentRequest,
    ResearchRunTargetRequest,
    RuntimeOptions,
)
from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.fetch import FetchRequest
from callus_research.models.source_bundle import ResearchIntent
from callus_research.models.university import UniversityTarget
from callus_research.models.verification import VerifyRequest
from callus_research.services.extract_from_html import extract_from_saved_html
from callus_research.services.extract_rules import build_placeholder_extraction
from callus_research.models.llm_retry_request import LLMRetryRequest
from callus_research.services.llm_field_adjudicator import adjudicate_weak_fields
from callus_research.services.research_workflow import process_research_input
from callus_research.services.source_discovery import discover_sources
from callus_research.services.source_fetcher import fetch_source
from callus_research.services.verify_fields import verify_extraction

router = APIRouter()


def apply_runtime_options(runtime: RuntimeOptions | None) -> None:
    if not runtime:
        return
    if runtime.llm_provider is not None:
        settings.llm_provider = runtime.llm_provider
    if runtime.llm_model is not None:
        settings.llm_model = runtime.llm_model
        settings.hf_model_id = runtime.llm_model or None
    if runtime.discovery_provider is not None:
        settings.discovery_provider = runtime.discovery_provider
    if runtime.discovery_model is not None:
        settings.discovery_model = runtime.discovery_model
    if runtime.hf_token is not None:
        settings.hf_token = runtime.hf_token or None
    if runtime.google_search_api_key is not None:
        settings.google_search_api_key = runtime.google_search_api_key or None
    if runtime.google_search_engine_id is not None:
        settings.google_search_engine_id = runtime.google_search_engine_id or None
    if runtime.vertex_search_project_id is not None:
        settings.vertex_search_project_id = runtime.vertex_search_project_id or None
    if runtime.vertex_search_location is not None:
        settings.vertex_search_location = runtime.vertex_search_location or "global"
    if runtime.vertex_search_data_store_id is not None:
        settings.vertex_search_data_store_id = runtime.vertex_search_data_store_id or None
    if runtime.vertex_search_serving_config_id is not None:
        settings.vertex_search_serving_config_id = (
            runtime.vertex_search_serving_config_id or "default_config"
        )
    if runtime.vertex_search_credentials_path is not None:
        settings.vertex_search_credentials_path = (
            runtime.vertex_search_credentials_path or None
        )


@router.get("/health")
async def health():
    return {"ok": True}


@router.post("/extract/placeholder")
async def extract_placeholder(target: UniversityTarget):
    record = build_placeholder_extraction(target)
    return {"ok": True, "data": record.model_dump()}


@router.post("/fetch/source")
async def fetch_source_route(request: FetchRequest):
    try:
        result = await fetch_source(request)
        return {"ok": True, "data": result.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/discover/sources")
async def discover_sources_route(intent: ResearchIntent):
    try:
        result = await discover_sources(intent)
        return {"ok": True, "data": result.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/research/run")
async def research_run_route(payload: ResearchRunIntentRequest):
    try:
        apply_runtime_options(payload.runtime)
        result = await process_research_input(payload.target)
        return {"ok": True, "data": result.model_dump(mode="json")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/research/run-target")
async def research_run_target_route(payload: ResearchRunTargetRequest):
    try:
        apply_runtime_options(payload.runtime)
        result = await process_research_input(payload.target)
        return {"ok": True, "data": result.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/extract/from-html")
async def extract_from_html_route(request: ExtractFromHtmlRequest):
    try:
        result = extract_from_saved_html(request)
        return {"ok": True, "data": result.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/verify/extraction")
async def verify_extraction_route(request: VerifyRequest):
    try:
        result = verify_extraction(request)
        return {"ok": True, "data": result.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/extract/llm-adjudicate")
@router.post("/extract/llm-retry")
async def extract_llm_retry_route(request: LLMRetryRequest):
    try:
        merged, escalations = adjudicate_weak_fields(
            request.html_request,
            request.verified_record,
        )
        return {
            "ok": True,
            "data": {
                "merged_record": merged.model_dump(),
                "field_escalations": [item.model_dump() for item in escalations],
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
