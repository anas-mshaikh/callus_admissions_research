import re
from typing import Iterable

from callus_research.models.extraction import FieldEvidence
from callus_research.models.verification import VerificationRecord


STATUS_SCORE = {
    "verified": 5,
    "adjudicated": 4,
    "corrected": 3,
    "unverified": 2,
    "uncertain": 1,
}

DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
    re.IGNORECASE,
)
FEE_RE = re.compile(r"(\$|USD|£|GBP)\s?\d{2,4}", re.IGNORECASE)


def value_quality_bonus(
    field_name: str, value: str | None, evidence_text: str | None
) -> int:
    if not value:
        return 0

    bonus = 0
    if field_name == "application_deadline" and DATE_RE.search(value):
        bonus += 5
    if field_name == "application_fee" and FEE_RE.search(value):
        bonus += 5
    if field_name == "english_proficiency" and len(value) > 12:
        bonus += 2
    if (
        field_name == "notable_requirement"
        and evidence_text
        and len(evidence_text) > len(value)
    ):
        bonus += 2

    return bonus


def field_score(field: FieldEvidence) -> int:
    return STATUS_SCORE.get(field.status, 0) + value_quality_bonus(
        field.field_name, field.value, field.evidence_text
    )


def choose_best_field(fields: Iterable[FieldEvidence]) -> FieldEvidence:
    fields = list(fields)
    return max(fields, key=field_score)


def merge_verification_records(records: list[VerificationRecord]) -> VerificationRecord:
    if not records:
        raise ValueError("No records to merge")

    base = records[0]

    return VerificationRecord(
        university_name=base.university_name,
        program_name=base.program_name,
        application_deadline=choose_best_field(
            [r.application_deadline for r in records]
        ),
        english_proficiency=choose_best_field([r.english_proficiency for r in records]),
        application_fee=choose_best_field([r.application_fee for r in records]),
        notable_requirement=choose_best_field([r.notable_requirement for r in records]),
    )
