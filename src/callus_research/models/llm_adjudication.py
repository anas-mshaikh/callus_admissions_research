from typing import Literal

from pydantic import BaseModel, Field


FieldName = Literal[
    "application_deadline",
    "english_proficiency",
    "application_fee",
    "notable_requirement",
]


class WeakFieldSignal(BaseModel):
    field_name: FieldName
    current_value: str | None = None
    current_status: str
    weakness_reason: str
    source_url: str
    supporting_snippets: list[str] = Field(default_factory=list)


class LLMAdjudicationResult(BaseModel):
    field_name: FieldName
    recommended_action: Literal["replace", "keep", "unresolved"] = "unresolved"
    value: str | None = Field(default=None, description="Best value for this field")
    evidence_text: str | None = Field(
        default=None,
        description="Short explanation or supporting evidence summary grounded in the snippets",
    )
    rationale: str | None = Field(
        default=None,
        description="Short reason why the current value should be kept, replaced, or left unresolved",
    )
    citation_type: Literal["snippet", "page", "none"] = "none"
    citation: str | None = Field(
        default=None,
        description="Short verbatim citation excerpt from the source snippets when available",
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class FieldEscalationResult(BaseModel):
    field_name: FieldName
    current_value: str | None = None
    current_status: str
    weakness_reason: str
    supporting_snippets: list[str] = Field(default_factory=list)
    adjudication: LLMAdjudicationResult | None = None
    resolved: bool = False
    final_value: str | None = None
    final_status: str
