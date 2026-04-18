from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


SourceType = Literal[
    "program_page",
    "application_checklist",
    "deadline_page",
    "english_requirements_page",
    "fee_page",
    "admissions_page",
    "other",
]


class SourcePage(BaseModel):
    url: HttpUrl
    source_type: SourceType = "other"
    mode: Literal["auto", "http", "browser"] = "auto"


class ResearchTarget(BaseModel):
    university_name: str
    country: str
    program_name: str
    sources: list[SourcePage] = Field(min_length=1)


class ResearchIntent(BaseModel):
    university_name: str
    country: str
    program_name: str
    degree_type: str
