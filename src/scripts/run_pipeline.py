import asyncio
import json
from pathlib import Path

from callus_research.models.source_bundle import ResearchTarget
from callus_research.services.export_results import (
    export_comparison_csv,
    export_final_records_json,
    export_target_results_json,
)
from callus_research.services.research_pipeline import process_research_target


INPUT_FILE = Path("data/inputs/universities.json")


def load_targets() -> list[ResearchTarget]:
    raw = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    return [ResearchTarget.model_validate(item) for item in raw]


async def main():
    targets = load_targets()
    results = []

    for target in targets:
        print(f"Processing: {target.university_name} | {target.program_name}")
        result = await process_research_target(target)
        results.append(result)

    target_json = export_target_results_json(results)
    final_json = export_final_records_json(results)
    csv_path = export_comparison_csv(results)

    print(f"Saved target results: {target_json}")
    print(f"Saved final records: {final_json}")
    print(f"Saved comparison CSV: {csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
