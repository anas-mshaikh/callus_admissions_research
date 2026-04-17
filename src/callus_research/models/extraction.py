from pydantic import BaseModel
from typing import Literal


class FieldEvidence(BaseModel):
    field_name: str
    value: str | None
    status: Literal["unverified", "verified", "corrected", "uncertain", "adjudicated"] = "unverified"
    evidence_text: str | None = None
    source_url: str | None = None


class ExtractionRecord(BaseModel):
    university_name: str
    program_name: str
    application_deadline: FieldEvidence
    english_proficiency: FieldEvidence
    application_fee: FieldEvidence
    notable_requirement: FieldEvidence
