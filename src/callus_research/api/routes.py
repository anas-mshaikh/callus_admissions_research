from fastapi import APIRouter, HTTPException

from callus_research.models.fetch import FetchRequest
from callus_research.models.university import UniversityTarget
from callus_research.services.extract_rules import build_placeholder_extraction
from callus_research.services.source_fetcher import fetch_source

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
