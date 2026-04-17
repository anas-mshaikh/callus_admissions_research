from pydantic import BaseModel

from callus_research.models.extraction import ExtractionRecord, FieldEvidence


class VerificationRecord(BaseModel):
    university_name: str
    program_name: str
    application_deadline: FieldEvidence
    english_proficiency: FieldEvidence
    application_fee: FieldEvidence
    notable_requirement: FieldEvidence


class VerifyRequest(BaseModel):
    extraction: ExtractionRecord
    saved_path: str
