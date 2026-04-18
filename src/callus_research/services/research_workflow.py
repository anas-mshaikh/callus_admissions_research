from __future__ import annotations

from callus_research.models.research_result import TargetResearchResult
from callus_research.models.source_bundle import ResearchIntent, ResearchTarget
from callus_research.services.research_pipeline import process_research_target
from callus_research.services.source_discovery import (
    build_research_target,
    discover_sources,
)


async def process_research_input(
    research_input: ResearchIntent | ResearchTarget,
) -> TargetResearchResult:
    if isinstance(research_input, ResearchTarget):
        return await process_research_target(research_input)

    discovery_result = await discover_sources(research_input)
    if not discovery_result.selected_sources:
        raise ValueError(
            "No official source URLs were selected during discovery. "
            f"Target: {research_input.university_name} | {research_input.program_name}"
        )

    target = build_research_target(research_input, discovery_result.selected_sources)
    result = await process_research_target(target)
    return result.model_copy(
        update={
            "degree_type": research_input.degree_type,
            "source_discovery": discovery_result,
        }
    )
