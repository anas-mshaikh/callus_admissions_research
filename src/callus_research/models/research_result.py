from pydantic import BaseModel, Field

from callus_research.models.extraction import ExtractionRecord
from callus_research.models.llm_adjudication import FieldEscalationResult
from callus_research.models.source_discovery import SourceDiscoveryResult
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
    field_escalations: list[FieldEscalationResult] = Field(default_factory=list)


class TargetResearchResult(BaseModel):
    university_name: str
    country: str
    program_name: str
    degree_type: str | None = None
    page_results: list[PageResearchResult]
    final_record: VerificationRecord
    source_discovery: SourceDiscoveryResult | None = None
