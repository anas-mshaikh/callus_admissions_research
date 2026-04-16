from callus_research.models.extraction import ExtractionRecord, FieldEvidence
from callus_research.models.university import UniversityTarget


def build_placeholder_extraction(target: UniversityTarget) -> ExtractionRecord:
    return ExtractionRecord(
        university_name=target.university_name,
        program_name=target.program_name,
        application_deadline=FieldEvidence(
            field_name="application_deadline", value=None, status="uncertain"
        ),
        english_proficiency=FieldEvidence(
            field_name="english_proficiency", value=None, status="uncertain"
        ),
        application_fee=FieldEvidence(
            field_name="application_fee", value=None, status="uncertain"
        ),
        notable_requirement=FieldEvidence(
            field_name="notable_requirement", value=None, status="uncertain"
        ),
    )
