from callus_research.models.verification import VerificationRecord, VerifyRequest
from callus_research.services.parse_html import html_to_text, read_html
from callus_research.services.verify_rules import (
    split_lines,
    verify_deadline,
    verify_english,
    verify_fee,
    verify_requirement,
)


def verify_extraction(request: VerifyRequest) -> VerificationRecord:
    html = read_html(request.saved_path)
    text = html_to_text(html)
    lines = split_lines(text)

    extraction = request.extraction

    application_deadline = verify_deadline(
        extraction.application_deadline,
        lines,
        extraction.application_deadline.source_url
        or extraction.application_fee.source_url
        or "",
    )
    english_proficiency = verify_english(
        extraction.english_proficiency,
        lines,
        extraction.english_proficiency.source_url
        or extraction.application_fee.source_url
        or "",
    )
    application_fee = verify_fee(
        extraction.application_fee,
        lines,
        extraction.application_fee.source_url
        or extraction.application_deadline.source_url
        or "",
    )
    notable_requirement = verify_requirement(
        extraction.notable_requirement,
        lines,
        extraction.notable_requirement.source_url
        or extraction.application_deadline.source_url
        or "",
    )

    return VerificationRecord(
        university_name=extraction.university_name,
        program_name=extraction.program_name,
        application_deadline=application_deadline,
        english_proficiency=english_proficiency,
        application_fee=application_fee,
        notable_requirement=notable_requirement,
    )
