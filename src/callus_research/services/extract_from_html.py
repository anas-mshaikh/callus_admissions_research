from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.extraction import ExtractionRecord
from callus_research.services.extract_rules import (
    extract_application_deadline,
    extract_application_fee,
    extract_english_proficiency,
    extract_notable_requirement,
    split_lines,
)
from callus_research.services.parse_html import html_to_text, read_html


def extract_from_saved_html(request: ExtractFromHtmlRequest) -> ExtractionRecord:
    html = read_html(request.saved_path)
    text = html_to_text(html)
    lines = split_lines(text)

    application_deadline = extract_application_deadline(lines)
    english_proficiency = extract_english_proficiency(lines)
    application_fee = extract_application_fee(lines)
    notable_requirement = extract_notable_requirement(lines)

    application_deadline.source_url = request.source_url
    english_proficiency.source_url = request.source_url
    application_fee.source_url = request.source_url
    notable_requirement.source_url = request.source_url

    return ExtractionRecord(
        university_name=request.university_name,
        program_name=request.program_name,
        application_deadline=application_deadline,
        english_proficiency=english_proficiency,
        application_fee=application_fee,
        notable_requirement=notable_requirement,
    )
