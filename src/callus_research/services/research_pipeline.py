from callus_research.logging_utils import get_logger
from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.fetch import FetchRequest
from callus_research.models.research_result import (
    PageResearchResult,
    TargetResearchResult,
)
from callus_research.models.source_bundle import ResearchTarget, SourcePage
from callus_research.models.verification import VerifyRequest
from callus_research.services.extract_from_html import extract_from_saved_html
from callus_research.services.llm_field_adjudicator import adjudicate_weak_fields
from callus_research.services.merge_records import merge_verification_records
from callus_research.services.source_fetcher import fetch_source
from callus_research.services.verify_fields import verify_extraction

logger = get_logger(__name__)


async def process_source_page(
    target: ResearchTarget,
    source: SourcePage,
) -> PageResearchResult:
    logger.info(
        "Processing source page: university=%s program=%s source_type=%s url=%s",
        target.university_name,
        target.program_name,
        source.source_type,
        source.url,
    )
    fetch_request = FetchRequest(
        university_name=target.university_name,
        country=target.country,
        program_name=target.program_name,
        source_url=source.url,
        mode=source.mode,
    )
    fetch_result = await fetch_source(fetch_request)
    logger.info(
        "Fetch completed: url=%s fetch_mode=%s content_length=%s",
        source.url,
        fetch_result.fetch_mode,
        fetch_result.content_length,
    )

    extract_request = ExtractFromHtmlRequest(
        university_name=target.university_name,
        country=target.country,
        program_name=target.program_name,
        source_url=str(source.url),
        saved_path=fetch_result.saved_path,
    )
    extracted = extract_from_saved_html(extract_request)
    logger.info(
        "Extraction completed: url=%s extracted_values=%s",
        source.url,
        {
            "application_deadline": bool(extracted.application_deadline.value),
            "english_proficiency": bool(extracted.english_proficiency.value),
            "application_fee": bool(extracted.application_fee.value),
            "notable_requirement": bool(extracted.notable_requirement.value),
        },
    )

    verified = verify_extraction(
        VerifyRequest(
            extraction=extracted,
            saved_path=fetch_result.saved_path,
        )
    )
    verified, field_escalations = adjudicate_weak_fields(extract_request, verified)
    logger.info(
        "Verification completed: url=%s escalations=%s final_statuses=%s",
        source.url,
        len(field_escalations),
        {
            "application_deadline": verified.application_deadline.status,
            "english_proficiency": verified.english_proficiency.status,
            "application_fee": verified.application_fee.status,
            "notable_requirement": verified.notable_requirement.status,
        },
    )

    return PageResearchResult(
        source_url=str(source.url),
        source_type=source.source_type,
        fetch_mode=fetch_result.fetch_mode,
        saved_path=fetch_result.saved_path,
        content_length=fetch_result.content_length,
        title=fetch_result.title,
        extracted=extracted,
        verified=verified,
        field_escalations=field_escalations,
    )


async def process_research_target(target: ResearchTarget) -> TargetResearchResult:
    if not target.sources:
        raise ValueError(
            f"No sources configured for {target.university_name} | {target.program_name}"
        )

    logger.info(
        "Starting target pipeline: university=%s program=%s sources=%s",
        target.university_name,
        target.program_name,
        len(target.sources),
    )
    page_results: list[PageResearchResult] = []

    for source in target.sources:
        page_result = await process_source_page(target, source)
        page_results.append(page_result)

    final_record = merge_verification_records([page.verified for page in page_results])
    logger.info(
        "Merge completed: university=%s program=%s final_statuses=%s",
        target.university_name,
        target.program_name,
        {
            "application_deadline": final_record.application_deadline.status,
            "english_proficiency": final_record.english_proficiency.status,
            "application_fee": final_record.application_fee.status,
            "notable_requirement": final_record.notable_requirement.status,
        },
    )

    return TargetResearchResult(
        university_name=target.university_name,
        country=target.country,
        program_name=target.program_name,
        degree_type=target.degree_type,
        page_results=page_results,
        final_record=final_record,
    )
