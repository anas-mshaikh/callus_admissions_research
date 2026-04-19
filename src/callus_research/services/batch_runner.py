from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Callable

from callus_research.logging_utils import get_logger
from callus_research.models.research_result import TargetResearchResult
from callus_research.models.source_bundle import ResearchIntent, ResearchTarget
from callus_research.services.export_results import (
    export_ai_vs_verified_csv,
    export_comparison_csv,
    export_correction_log_csv,
    export_final_records_json,
    export_source_discovery_json,
    export_target_results_json,
)
from callus_research.services.research_workflow import process_research_input


DEFAULT_INPUT_FILE = Path("data/inputs/universities.json")
logger = get_logger(__name__)

ResearchInput = ResearchIntent | ResearchTarget
ProgressCallback = Callable[[str, int, int, ResearchInput], None]


def parse_research_input(item: dict) -> ResearchInput:
    if "sources" in item:
        return ResearchTarget.model_validate(item)
    return ResearchIntent.model_validate(item)


def load_targets(input_file: Path = DEFAULT_INPUT_FILE) -> list[ResearchInput]:
    raw = json.loads(input_file.read_text(encoding="utf-8"))
    return [parse_research_input(item) for item in raw]


def parse_targets_json(raw_json: str) -> list[ResearchInput]:
    payload = json.loads(raw_json)
    if not isinstance(payload, list):
        raise ValueError("Target payload must be a JSON array.")
    return [parse_research_input(item) for item in payload]


def serialize_targets(targets: list[ResearchInput]) -> str:
    payload = [target.model_dump(mode="json") for target in targets]
    return json.dumps(payload, indent=2, ensure_ascii=False)


async def run_targets(
    targets: list[ResearchInput],
    progress_callback: ProgressCallback | None = None,
) -> list[TargetResearchResult]:
    results: list[TargetResearchResult] = []
    total = len(targets)
    logger.info("Starting batch run for %s target(s)", total)

    for index, target in enumerate(targets, start=1):
        logger.info(
            "Starting target %s/%s: university=%s program=%s mode=%s",
            index,
            total,
            target.university_name,
            target.program_name,
            "manual" if isinstance(target, ResearchTarget) else "discovery",
        )
        if progress_callback:
            progress_callback("discover", index, total, target)
        result = await process_research_input(target)
        results.append(result)
        logger.info(
            "Completed target %s/%s: university=%s program=%s pages=%s",
            index,
            total,
            result.university_name,
            result.program_name,
            len(result.page_results),
        )
        if progress_callback:
            progress_callback("complete", index, total, target)

    logger.info("Finished batch run with %s result(s)", len(results))
    return results


def run_targets_sync(
    targets: list[ResearchInput],
    progress_callback: ProgressCallback | None = None,
) -> list[TargetResearchResult]:
    return asyncio.run(run_targets(targets, progress_callback=progress_callback))


def export_results_bundle(results: list[TargetResearchResult]) -> dict[str, Path]:
    export_paths = {
        "target_results": export_target_results_json(results),
        "final_records": export_final_records_json(results),
        "comparison_csv": export_comparison_csv(results),
        "source_discovery": export_source_discovery_json(results),
        "ai_vs_verified": export_ai_vs_verified_csv(results),
        "correction_log": export_correction_log_csv(results),
    }
    logger.info("Exported result bundle to %s", export_paths["target_results"].parent)
    return export_paths
