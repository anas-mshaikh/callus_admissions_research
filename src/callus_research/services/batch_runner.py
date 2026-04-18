from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Callable

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

    for index, target in enumerate(targets, start=1):
        if progress_callback:
            progress_callback("discover", index, total, target)
        results.append(await process_research_input(target))
        if progress_callback:
            progress_callback("complete", index, total, target)

    return results


def run_targets_sync(
    targets: list[ResearchInput],
    progress_callback: ProgressCallback | None = None,
) -> list[TargetResearchResult]:
    return asyncio.run(run_targets(targets, progress_callback=progress_callback))


def export_results_bundle(results: list[TargetResearchResult]) -> dict[str, Path]:
    return {
        "target_results": export_target_results_json(results),
        "final_records": export_final_records_json(results),
        "comparison_csv": export_comparison_csv(results),
        "source_discovery": export_source_discovery_json(results),
        "ai_vs_verified": export_ai_vs_verified_csv(results),
        "correction_log": export_correction_log_csv(results),
    }
