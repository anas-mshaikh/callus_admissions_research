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


def export_source_discovery_json(
    results: list[TargetResearchResult],
    filename: str = "source_discovery.json",
) -> Path:
    output_dir = ensure_output_dir()
    path = output_dir / filename
    payload = [
        result.source_discovery.model_dump()
        for result in results
        if result.source_discovery is not None
    ]
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


def export_ai_vs_verified_csv(
    results: list[TargetResearchResult],
    filename: str = "ai_vs_verified.csv",
) -> Path:
    output_dir = ensure_output_dir()
    path = output_dir / filename

    rows = []
    field_names = [
        "application_deadline",
        "english_proficiency",
        "application_fee",
        "notable_requirement",
    ]

    for result in results:
        final_record = result.final_record
        for field_name in field_names:
            initial_value = None
            initial_status = None
            initial_source_url = None
            for page_result in result.page_results:
                extracted = getattr(page_result.extracted, field_name)
                if extracted.value:
                    initial_value = extracted.value
                    initial_status = extracted.status
                    initial_source_url = page_result.source_url
                    break

            final_field = getattr(final_record, field_name)
            rows.append(
                {
                    "university_name": result.university_name,
                    "program_name": result.program_name,
                    "degree_type": result.degree_type,
                    "field_name": field_name,
                    "generated_value": initial_value,
                    "generated_status": initial_status,
                    "generated_source_url": initial_source_url,
                    "verified_value": final_field.value,
                    "verified_status": final_field.status,
                    "verified_source_url": final_field.source_url,
                    "official_evidence": final_field.evidence_text,
                }
            )

    fieldnames = [
        "university_name",
        "program_name",
        "degree_type",
        "field_name",
        "generated_value",
        "generated_status",
        "generated_source_url",
        "verified_value",
        "verified_status",
        "verified_source_url",
        "official_evidence",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return path


def export_correction_log_csv(
    results: list[TargetResearchResult],
    filename: str = "correction_log.csv",
) -> Path:
    output_dir = ensure_output_dir()
    path = output_dir / filename

    rows = []
    for result in results:
        for page_result in result.page_results:
            for escalation in page_result.field_escalations:
                adjudication = escalation.adjudication
                rows.append(
                    {
                        "university_name": result.university_name,
                        "program_name": result.program_name,
                        "degree_type": result.degree_type,
                        "source_url": page_result.source_url,
                        "field_name": escalation.field_name,
                        "initial_value": escalation.current_value,
                        "initial_status": escalation.current_status,
                        "weakness_reason": escalation.weakness_reason,
                        "final_value": escalation.final_value,
                        "final_status": escalation.final_status,
                        "resolved": escalation.resolved,
                        "llm_action": adjudication.recommended_action
                        if adjudication
                        else None,
                        "citation_type": adjudication.citation_type
                        if adjudication
                        else None,
                        "citation": adjudication.citation if adjudication else None,
                        "rationale": adjudication.rationale if adjudication else None,
                    }
                )

    fieldnames = [
        "university_name",
        "program_name",
        "degree_type",
        "source_url",
        "field_name",
        "initial_value",
        "initial_status",
        "weakness_reason",
        "final_value",
        "final_status",
        "resolved",
        "llm_action",
        "citation_type",
        "citation",
        "rationale",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return path
