import re
from typing import Iterable

from callus_research.models.extraction import ExtractionRecord, FieldEvidence
from callus_research.models.university import UniversityTarget


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

ENGLISH_KEYWORDS = [
    "ielts",
    "toefl",
    "duolingo",
    "english language",
    "english proficiency",
    "cambridge english",
]

NOTABLE_REQUIREMENT_KEYWORDS = [
    "letters of recommendation",
    "recommendation letters",
    "statement of purpose",
    "personal statement",
    "writing sample",
    "cv",
    "resume",
    "interview",
    "portfolio",
    "references",
    "essays",
]


def build_placeholder_extraction(target: UniversityTarget) -> ExtractionRecord:
    return ExtractionRecord(
        university_name=target.university_name,
        program_name=target.program_name,
        application_deadline=FieldEvidence(field_name="application_deadline"),
        english_proficiency=FieldEvidence(field_name="english_proficiency"),
        application_fee=FieldEvidence(field_name="application_fee"),
        notable_requirement=FieldEvidence(field_name="notable_requirement"),
    )


def split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def find_first_matching_line(lines: Iterable[str], keywords: list[str]) -> str | None:
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            return line
    return None


def find_first_regex_match(lines: Iterable[str], patterns: list[str]) -> str | None:
    for line in lines:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return line
    return None


def clean_value_from_line(
    line: str | None, patterns: list[str] | None = None
) -> str | None:
    if not line:
        return None

    if patterns:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(0)

    return line


def extract_application_deadline(lines: list[str]) -> FieldEvidence:
    keywords = ["deadline", "application deadline", "apply by", "submission deadline"]
    keyword_line = find_first_matching_line(lines, keywords)
    regex_line = find_first_regex_match(lines, DATE_PATTERNS)

    chosen_line = keyword_line or regex_line
    value = clean_value_from_line(chosen_line, DATE_PATTERNS)

    return FieldEvidence(
        field_name="application_deadline",
        value=value,
        status="unverified" if value else "uncertain",
        evidence_text=chosen_line,
    )


def extract_english_proficiency(lines: list[str]) -> FieldEvidence:
    line = find_first_matching_line(lines, ENGLISH_KEYWORDS)

    return FieldEvidence(
        field_name="english_proficiency",
        value=line,
        status="unverified" if line else "uncertain",
        evidence_text=line,
    )


def extract_application_fee(lines: list[str]) -> FieldEvidence:
    fee_keywords = ["application fee", "fee", "non-refundable fee"]
    keyword_line = find_first_matching_line(lines, fee_keywords)
    regex_line = find_first_regex_match(lines, FEE_PATTERNS)

    chosen_line = keyword_line or regex_line
    value = clean_value_from_line(chosen_line, FEE_PATTERNS)

    return FieldEvidence(
        field_name="application_fee",
        value=value,
        status="unverified" if value else "uncertain",
        evidence_text=chosen_line,
    )


def extract_notable_requirement(lines: list[str]) -> FieldEvidence:
    line = find_first_matching_line(lines, NOTABLE_REQUIREMENT_KEYWORDS)

    return FieldEvidence(
        field_name="notable_requirement",
        value=line,
        status="unverified" if line else "uncertain",
        evidence_text=line,
    )
