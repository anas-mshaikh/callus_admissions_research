from pydantic import BaseModel, Field


class LLMField(BaseModel):
    value: str | None = Field(default=None, description="Best extracted value")
    evidence_text: str | None = Field(
        default=None, description="Short evidence snippet copied from the page text"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class LLMExtractionResult(BaseModel):
    application_deadline: LLMField
    english_proficiency: LLMField
    application_fee: LLMField
    notable_requirement: LLMField
