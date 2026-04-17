from fastapi import APIRouter, HTTPException

from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.fetch import FetchRequest
from callus_research.models.university import UniversityTarget
from callus_research.models.verification import VerifyRequest
from callus_research.services.extract_from_html import extract_from_saved_html
from callus_research.services.extract_rules import build_placeholder_extraction
from callus_research.services.source_fetcher import fetch_source
from callus_research.services.verify_fields import verify_extraction
from callus_research.models.llm_retry_request import LLMRetryRequest
from callus_research.services.extract_llm import extract_with_llm
from callus_research.services.merge_llm_retry import merge_llm_result

router = APIRouter()


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


@router.post("/extract/llm-retry")
async def extract_llm_retry_route(request: LLMRetryRequest):
    try:
        llm_result = extract_with_llm(request.html_request)
        merged = merge_llm_result(
            record=request.verified_record,
            llm_result=llm_result,
            source_url=request.html_request.source_url,
        )
        return {
            "ok": True,
            "data": {
                "llm_result": llm_result.model_dump(),
                "merged_record": merged.model_dump(),
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))