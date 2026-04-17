import re
from typing import Iterable

from callus_research.models.extraction import FieldEvidence


MONTH_PATTERN = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
DATE_PATTERNS = [
    rf"\b{MONTH_PATTERN}\s+\d{{1,2}},\s+\d{{4}}\b",
    rf"\b\d{{1,2}}\s+{MONTH_PATTERN}\s+\d{{4}}\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
]

FEE_PATTERNS = [
    r"\$\s?\d{2,4}",
    r"USD\s?\d{2,4}",
    r"£\s?\d{2,4}",
    r"GBP\s?\d{2,4}",
]

ENGLISH_PATTERNS = [
    r"\btoefl\b",
    r"\bielts\b",
    r"\bduolingo\b",
    r"\benglish language\b",
    r"\benglish proficiency\b",
    r"\bcambridge english\b",
]

GENERIC_BAD_VALUES = {
    "application fee",
    "graduate application deadlines",
    "deadline",
    "deadlines",
    "fee",
    "english proficiency",
    "statement of purpose",
}


def split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def is_generic_label(value: str | None) -> bool:
    if not value:
        return True
    return value.strip().lower() in GENERIC_BAD_VALUES


def find_first_pattern(
    lines: Iterable[str], patterns: list[str]
) -> tuple[str | None, str | None]:
    for line in lines:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(0), line
    return None, None


def find_first_line_with_keywords(
    lines: Iterable[str], keywords: list[str]
) -> str | None:
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            return line
    return None


def verify_deadline(
    field: FieldEvidence, lines: list[str], source_url: str
) -> FieldEvidence:
    if field.value and not is_generic_label(field.value):
        for pattern in DATE_PATTERNS:
            if re.search(pattern, field.value, re.IGNORECASE):
                field.status = "verified"
                field.source_url = source_url
                return field

    value, evidence = find_first_pattern(lines, DATE_PATTERNS)
    if value:
        return FieldEvidence(
            field_name=field.field_name,
            value=value,
            status="corrected",
            evidence_text=evidence,
            source_url=source_url,
        )

    field.status = "uncertain"
    field.source_url = source_url
    return field


def verify_fee(
    field: FieldEvidence, lines: list[str], source_url: str
) -> FieldEvidence:
    if field.value and not is_generic_label(field.value):
        for pattern in FEE_PATTERNS:
            if re.search(pattern, field.value, re.IGNORECASE):
                field.status = "verified"
                field.source_url = source_url
                return field

    value, evidence = find_first_pattern(lines, FEE_PATTERNS)
    if value:
        return FieldEvidence(
            field_name=field.field_name,
            value=value,
            status="corrected",
            evidence_text=evidence,
            source_url=source_url,
        )

    field.status = "uncertain"
    field.source_url = source_url
    return field


def verify_english(
    field: FieldEvidence, lines: list[str], source_url: str
) -> FieldEvidence:
    if field.value and not is_generic_label(field.value):
        for pattern in ENGLISH_PATTERNS:
            if re.search(pattern, field.value, re.IGNORECASE):
                field.status = "verified"
                field.source_url = source_url
                return field

    value = find_first_line_with_keywords(
        lines,
        [
            "toefl",
            "ielts",
            "duolingo",
            "english language",
            "english proficiency",
            "cambridge english",
        ],
    )
    if value:
        return FieldEvidence(
            field_name=field.field_name,
            value=value,
            status="corrected" if field.value != value else "verified",
            evidence_text=value,
            source_url=source_url,
        )

    field.status = "uncertain"
    field.source_url = source_url
    return field


def verify_requirement(
    field: FieldEvidence, lines: list[str], source_url: str
) -> FieldEvidence:
    requirement_keywords = [
        "statement of purpose",
        "personal statement",
        "letters of recommendation",
        "recommendation letters",
        "resume",
        "cv",
        "interview",
        "writing sample",
        "essays",
        "references",
    ]

    if field.value and not is_generic_label(field.value):
        field.status = "verified"
        field.source_url = source_url
        return field

    value = find_first_line_with_keywords(lines, requirement_keywords)
    if value:
        return FieldEvidence(
            field_name=field.field_name,
            value=value,
            status="corrected",
            evidence_text=value,
            source_url=source_url,
        )

    field.status = "uncertain"
    field.source_url = source_url
    return field
