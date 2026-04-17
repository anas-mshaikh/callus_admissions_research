import csv
import json
from pathlib import Path

from callus_research.config import settings
from callus_research.models.research_result import TargetResearchResult


def ensure_output_dir() -> Path:
    output_dir = settings.data_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def export_target_results_json(
    results: list[TargetResearchResult],
    filename: str = "target_results.json",
) -> Path:
    output_dir = ensure_output_dir()
    path = output_dir / filename
    payload = [result.model_dump() for result in results]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def export_final_records_json(
    results: list[TargetResearchResult],
    filename: str = "final_records.json",
) -> Path:
    output_dir = ensure_output_dir()
    path = output_dir / filename
    payload = [result.final_record.model_dump() for result in results]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def export_comparison_csv(
    results: list[TargetResearchResult],
    filename: str = "comparison_table.csv",
) -> Path:
    output_dir = ensure_output_dir()
    path = output_dir / filename

    rows = []
    for result in results:
        record = result.final_record
        rows.append(
            {
                "university_name": result.university_name,
                "country": result.country,
                "program_name": result.program_name,
                "application_deadline": record.application_deadline.value,
                "application_deadline_status": record.application_deadline.status,
                "application_deadline_source_url": record.application_deadline.source_url,
                "english_proficiency": record.english_proficiency.value,
                "english_proficiency_status": record.english_proficiency.status,
                "english_proficiency_source_url": record.english_proficiency.source_url,
                "application_fee": record.application_fee.value,
                "application_fee_status": record.application_fee.status,
                "application_fee_source_url": record.application_fee.source_url,
                "notable_requirement": record.notable_requirement.value,
                "notable_requirement_status": record.notable_requirement.status,
                "notable_requirement_source_url": record.notable_requirement.source_url,
            }
        )

    fieldnames = [
        "university_name",
        "country",
        "program_name",
        "application_deadline",
        "application_deadline_status",
        "application_deadline_source_url",
        "english_proficiency",
        "english_proficiency_status",
        "english_proficiency_source_url",
        "application_fee",
        "application_fee_status",
        "application_fee_source_url",
        "notable_requirement",
        "notable_requirement_status",
        "notable_requirement_source_url",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return path
