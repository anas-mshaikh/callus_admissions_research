from callus_research.models.extraction import FieldEvidence
from callus_research.models.verification import VerificationRecord
from callus_research.models.llm_extract import LLMExtractionResult


LOW_QUALITY_VALUES = {
    None,
    "",
    "application fee",
    "graduate application deadlines",
    "deadline",
    "deadlines",
    "fee",
}


def should_replace(field: FieldEvidence) -> bool:
    if field.status in {"uncertain"}:
        return True
    if field.value in LOW_QUALITY_VALUES:
        return True
    return False


def upgrade_field(original: FieldEvidence, llm_value, source_url: str) -> FieldEvidence:
    if not llm_value or not llm_value.value:
        return original

    if should_replace(original):
        return FieldEvidence(
            field_name=original.field_name,
            value=llm_value.value,
            status="corrected",
            evidence_text=llm_value.evidence_text,
            source_url=source_url,
        )

    return original


def merge_llm_result(
    record: VerificationRecord,
    llm_result: LLMExtractionResult,
    source_url: str,
) -> VerificationRecord:
    record.application_deadline = upgrade_field(
        record.application_deadline, llm_result.application_deadline, source_url
    )
    record.english_proficiency = upgrade_field(
        record.english_proficiency, llm_result.english_proficiency, source_url
    )
    record.application_fee = upgrade_field(
        record.application_fee, llm_result.application_fee, source_url
    )
    record.notable_requirement = upgrade_field(
        record.notable_requirement, llm_result.notable_requirement, source_url
    )

    return record
