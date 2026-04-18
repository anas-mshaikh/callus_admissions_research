from typing import Literal

from pydantic import BaseModel, Field

from callus_research.models.source_bundle import SourcePage, SourceType


class DiscoveredSourceCandidate(BaseModel):
    source_type: SourceType
    query: str
    url: str
    title: str | None = None
    reason: str
    confidence: float = 0.0
    selected: bool = False
    rejection_reason: str | None = None
    is_official: bool = False


class SourceDiscoveryResult(BaseModel):
    university_name: str
    country: str
    program_name: str
    degree_type: str
    search_queries: list[str] = Field(default_factory=list)
    candidates: list[DiscoveredSourceCandidate] = Field(default_factory=list)
    selected_sources: list[SourcePage] = Field(default_factory=list)
    summary: str | None = None
