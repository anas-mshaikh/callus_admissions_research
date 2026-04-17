from pydantic import BaseModel

from callus_research.models.extraction import ExtractionRecord
from callus_research.models.verification import VerificationRecord


class PageResearchResult(BaseModel):
    source_url: str
    source_type: str
    fetch_mode: str
    saved_path: str
    content_length: int
    title: str | None = None
    extracted: ExtractionRecord
    verified: VerificationRecord


class TargetResearchResult(BaseModel):
    university_name: str
    country: str
    program_name: str
    page_results: list[PageResearchResult]
    final_record: VerificationRecord
