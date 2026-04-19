from __future__ import annotations

from callus_research.logging_utils import get_logger
from callus_research.models.research_result import TargetResearchResult
from callus_research.models.source_bundle import ResearchIntent, ResearchTarget
from callus_research.services.research_pipeline import process_research_target
from callus_research.services.source_discovery import (
    build_research_target,
    discover_sources,
)

logger = get_logger(__name__)


async def process_research_input(
    research_input: ResearchIntent | ResearchTarget,
) -> TargetResearchResult:
    if isinstance(research_input, ResearchTarget):
        logger.info(
            "Bypassing discovery for manual target: university=%s program=%s sources=%s",
            research_input.university_name,
            research_input.program_name,
            len(research_input.sources),
        )
        return await process_research_target(research_input)

    logger.info(
        "Starting source discovery: university=%s program=%s degree=%s",
        research_input.university_name,
        research_input.program_name,
        research_input.degree_type,
    )
    discovery_result = await discover_sources(research_input)
    if not discovery_result.selected_sources:
        logger.warning(
            "No official sources selected during discovery: university=%s program=%s candidates=%s",
            research_input.university_name,
            research_input.program_name,
            len(discovery_result.candidates),
        )
        raise ValueError(
            "No official source URLs were selected during discovery. "
            f"Target: {research_input.university_name} | {research_input.program_name}"
        )

    logger.info(
        "Discovery selected %s source(s): university=%s program=%s",
        len(discovery_result.selected_sources),
        research_input.university_name,
        research_input.program_name,
    )
    target = build_research_target(research_input, discovery_result.selected_sources)
    result = await process_research_target(target)
    return result.model_copy(
        update={
            "degree_type": research_input.degree_type,
            "source_discovery": discovery_result,
        }
    )
