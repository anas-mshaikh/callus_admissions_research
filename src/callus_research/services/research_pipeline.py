from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.fetch import FetchRequest
from callus_research.models.research_result import (
    PageResearchResult,
    TargetResearchResult,
)
from callus_research.models.source_bundle import ResearchTarget, SourcePage
from callus_research.models.verification import VerificationRecord, VerifyRequest
from callus_research.services.extract_from_html import extract_from_saved_html
from callus_research.services.extract_llm import extract_with_llm
from callus_research.services.merge_llm_retry import merge_llm_result
from callus_research.services.merge_records import merge_verification_records
from callus_research.services.source_fetcher import fetch_source
from callus_research.services.verify_fields import verify_extraction


def record_needs_llm_retry(record: VerificationRecord) -> bool:
    return any(
        field.status == "uncertain"
        for field in [
            record.application_deadline,
            record.english_proficiency,
            record.application_fee,
            record.notable_requirement,
        ]
    )


async def process_source_page(
    target: ResearchTarget,
    source: SourcePage,
) -> PageResearchResult:
    fetch_request = FetchRequest(
        university_name=target.university_name,
        country=target.country,
        program_name=target.program_name,
        source_url=source.url,
        mode=source.mode,
    )
    fetch_result = await fetch_source(fetch_request)

    extract_request = ExtractFromHtmlRequest(
        university_name=target.university_name,
        country=target.country,
        program_name=target.program_name,
        source_url=str(source.url),
        saved_path=fetch_result.saved_path,
    )
    extracted = extract_from_saved_html(extract_request)

    verified = verify_extraction(
        VerifyRequest(
            extraction=extracted,
            saved_path=fetch_result.saved_path,
        )
    )

    if record_needs_llm_retry(verified):
        llm_result = extract_with_llm(extract_request)
        verified = merge_llm_result(
            record=verified,
            llm_result=llm_result,
            source_url=str(source.url),
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
    )


async def process_research_target(target: ResearchTarget) -> TargetResearchResult:
    page_results: list[PageResearchResult] = []

    for source in target.sources:
        page_result = await process_source_page(target, source)
        page_results.append(page_result)

    final_record = merge_verification_records([page.verified for page in page_results])

    return TargetResearchResult(
        university_name=target.university_name,
        country=target.country,
        program_name=target.program_name,
        page_results=page_results,
        final_record=final_record,
    )
