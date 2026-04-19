from pydantic import BaseModel, Field

from callus_research.models.source_common import SourcePage


class ResearchTarget(BaseModel):
    university_name: str
    country: str
    program_name: str
    degree_type: str | None = None
    sources: list[SourcePage] = Field(min_length=1)


class ResearchIntent(BaseModel):
    university_name: str
    country: str
    program_name: str
    degree_type: str
