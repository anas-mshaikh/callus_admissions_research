from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import httpx
import streamlit as st
from pydantic import ValidationError

from callus_research.config import settings
from callus_research.models.api_requests import RuntimeOptions
from callus_research.models.research_result import TargetResearchResult
from callus_research.models.source_bundle import (
    ResearchIntent,
    ResearchTarget,
    SourcePage,
)

DEGREE_TYPES = ["Master's", "PhD", "Bachelor's", "MPhil", "Other"]
SOURCE_TYPES = [
    "program_page",
    "application_checklist",
    "deadline_page",
    "english_requirements_page",
    "fee_page",
    "admissions_page",
    "other",
]
FETCH_MODES = ["auto", "http", "browser"]
LLM_PROVIDERS = ["openai", "gemini", "hf_inference"]
MANUAL_DISCOVERY_PROVIDER = "manual"
DISCOVERY_PROVIDERS = [
    MANUAL_DISCOVERY_PROVIDER,
    "adk_google_search",
    "google_custom_search",
    "vertex_ai_search",
]

FIELD_NAMES: tuple[str, ...] = (
    "application_deadline",
    "english_proficiency",
    "application_fee",
    "notable_requirement",
)

FIELD_LABELS = {
    "application_deadline": "Application deadline",
    "english_proficiency": "English requirement",
    "application_fee": "Application fee",
    "notable_requirement": "Notable requirement",
}

STATUS_LABELS = {
    "verified": "Confirmed on source page",
    "corrected": "Corrected from source page",
    "adjudicated": "Resolved from source evidence",
    "unverified": "Needs review",
    "uncertain": "Still unclear",
    "unknown": "Unknown",
}

FINAL_OK_STATUSES: set[str] = {"verified", "corrected", "adjudicated"}

ACTION_LABELS = {
    "replace": "Updated answer",
    "keep": "Kept answer",
    "unresolved": "Could not resolve",
}

REASON_REWRITES = {
    "rule-based verification could not confirm a supported value": "Could not confirm this from the source page",
    "no usable value is present": "No usable answer was found",
    "the current value is a generic label instead of a concrete answer": "The extracted text was too generic",
    "the deadline value does not contain a specific date pattern": "No specific deadline date was found",
    "the fee value does not contain a concrete currency amount": "No fee amount was found",
    "the english requirement does not mention a recognizable test or requirement phrase": "No clear English test requirement was found",
    "the requirement value is too short to be confidently useful": "The requirement detail was too short",
    "the current value has no supporting evidence snippet": "No supporting quote was found",
}


def apply_runtime_settings() -> None:
    return None


def safe_attr(obj: Any, attr_name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    return getattr(obj, attr_name, default)


def normalize_status(value: Any) -> str:
    status = safe_attr(value, "status", None)
    if isinstance(status, str) and status.strip():
        return status.strip()
    return "unknown"


def iter_record_fields(record: Any) -> list[tuple[str, Any]]:
    fields: list[tuple[str, Any]] = []
    for field_name in FIELD_NAMES:
        field_value = getattr(record, field_name, None)
        if field_value is not None:
            fields.append((field_name, field_value))
    return fields


def coerce_choice(value: str | None, allowed: list[str], fallback: str) -> str:
    if value in allowed:
        return value
    return fallback


def init_session_state() -> None:
    defaults = {
        "results": [],
        "export_payloads": {},
        "ui_backend_base_url": "http://127.0.0.1:8000",
        "ui_llm_provider": coerce_choice(
            getattr(settings, "llm_provider", None), LLM_PROVIDERS, "openai"
        ),
        "ui_llm_model": getattr(settings, "llm_model", "") or "",
        "ui_discovery_provider": coerce_choice(
            getattr(settings, "discovery_provider", None),
            DISCOVERY_PROVIDERS,
            MANUAL_DISCOVERY_PROVIDER,
        ),
        "ui_discovery_model": getattr(settings, "discovery_model", "") or "",
        "ui_hf_token": getattr(settings, "hf_token", "") or "",
        "ui_google_search_api_key": "",
        "ui_google_search_engine_id": getattr(settings, "google_search_engine_id", "")
        or "",
        "ui_vertex_search_project_id": getattr(settings, "vertex_search_project_id", "")
        or "",
        "ui_vertex_search_location": getattr(settings, "vertex_search_location", "")
        or "global",
        "ui_vertex_search_data_store_id": getattr(
            settings, "vertex_search_data_store_id", ""
        )
        or "",
        "ui_vertex_search_serving_config_id": getattr(
            settings, "vertex_search_serving_config_id", ""
        )
        or "default_config",
        "ui_vertex_search_credentials_path": getattr(
            settings, "vertex_search_credentials_path", ""
        )
        or "",
        "ui_manual_source_urls": "",
        "ui_manual_source_type": "program_page",
        "ui_manual_fetch_mode": "auto",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def build_runtime_options() -> RuntimeOptions:
    discovery_provider = st.session_state["ui_discovery_provider"]

    return RuntimeOptions(
        llm_provider=st.session_state["ui_llm_provider"],
        llm_model=st.session_state["ui_llm_model"].strip() or None,
        discovery_provider=None
        if discovery_provider == MANUAL_DISCOVERY_PROVIDER
        else discovery_provider,
        discovery_model=st.session_state["ui_discovery_model"].strip() or None,
        hf_token=st.session_state["ui_hf_token"].strip() or None,
        google_search_api_key=st.session_state["ui_google_search_api_key"].strip()
        or None,
        google_search_engine_id=st.session_state["ui_google_search_engine_id"].strip()
        or None,
        vertex_search_project_id=st.session_state["ui_vertex_search_project_id"].strip()
        or None,
        vertex_search_location=st.session_state["ui_vertex_search_location"].strip()
        or None,
        vertex_search_data_store_id=st.session_state[
            "ui_vertex_search_data_store_id"
        ].strip()
        or None,
        vertex_search_serving_config_id=st.session_state[
            "ui_vertex_search_serving_config_id"
        ].strip()
        or None,
        vertex_search_credentials_path=st.session_state[
            "ui_vertex_search_credentials_path"
        ].strip()
        or None,
    )


def csv_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""

    import csv

    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def build_export_payloads(results: list[TargetResearchResult]) -> dict[str, str]:
    return {
        "target_results": json.dumps(
            [result.model_dump(mode="json") for result in results],
            indent=2,
            ensure_ascii=False,
        ),
        "final_records": json.dumps(
            [result.final_record.model_dump(mode="json") for result in results],
            indent=2,
            ensure_ascii=False,
        ),
        "comparison_csv": csv_text(final_comparison_rows(results)),
        "source_discovery": json.dumps(
            source_discovery_rows(results), indent=2, ensure_ascii=False
        ),
        "ai_vs_verified": csv_text(ai_vs_verified_rows(results)),
        "correction_log": csv_text(correction_rows(results)),
    }


def backend_base_url() -> str:
    return st.session_state["ui_backend_base_url"].rstrip("/")


def build_intent_from_form(
    university_name: str,
    country: str,
    program_name: str,
    degree_type: str,
) -> ResearchIntent:
    return ResearchIntent.model_validate(
        {
            "university_name": university_name.strip(),
            "country": country.strip(),
            "program_name": program_name.strip(),
            "degree_type": degree_type.strip(),
        }
    )


def parse_manual_source_pages(
    source_urls_text: str,
    default_source_type: str,
    default_fetch_mode: str,
) -> list[SourcePage]:
    source_pages: list[SourcePage] = []

    for line_number, raw_line in enumerate(source_urls_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = [part.strip() for part in line.split("|")]
        if len(parts) > 3:
            raise ValueError(
                "Manual source lines must use 'url', 'url | source_type', "
                f"or 'url | source_type | mode'. Problem on line {line_number}."
            )

        url = parts[0]
        source_type = parts[1] if len(parts) >= 2 and parts[1] else default_source_type
        fetch_mode = parts[2] if len(parts) == 3 and parts[2] else default_fetch_mode

        try:
            source_pages.append(
                SourcePage.model_validate(
                    {
                        "url": url,
                        "source_type": source_type,
                        "mode": fetch_mode,
                    }
                )
            )
        except ValidationError as exc:
            raise ValueError(
                f"Invalid manual source on line {line_number}: {exc}"
            ) from exc

    if not source_pages:
        raise ValueError("Enter at least one manual source URL.")

    return source_pages


def build_manual_target_from_form(
    university_name: str,
    country: str,
    program_name: str,
    degree_type: str,
    source_urls_text: str,
    default_source_type: str,
    default_fetch_mode: str,
) -> ResearchTarget:
    source_pages = parse_manual_source_pages(
        source_urls_text=source_urls_text,
        default_source_type=default_source_type,
        default_fetch_mode=default_fetch_mode,
    )

    return ResearchTarget.model_validate(
        {
            "university_name": university_name.strip(),
            "country": country.strip(),
            "program_name": program_name.strip(),
            "degree_type": degree_type.strip(),
            "sources": [page.model_dump(mode="json") for page in source_pages],
        }
    )


def simplify_reason(reason: str | None) -> str | None:
    if not reason:
        return reason

    simplified = reason
    for source, replacement in REASON_REWRITES.items():
        simplified = simplified.replace(source, replacement)
    return simplified.replace("; ", " | ")


def record_to_rows(record: Any) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []

    for field_name, field in iter_record_fields(record):
        raw_status = normalize_status(field)
        rows.append(
            {
                "Requirement": FIELD_LABELS.get(field_name, field_name),
                "Answer": safe_attr(field, "value"),
                "Result": STATUS_LABELS.get(raw_status, raw_status),
                "Source page": safe_attr(field, "source_url"),
                "Evidence": safe_attr(field, "evidence_text"),
            }
        )

    return rows


def escalation_to_rows(field_escalations: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for escalation in field_escalations:
        adjudication = safe_attr(escalation, "adjudication")
        rows.append(
            {
                "Requirement": FIELD_LABELS.get(
                    safe_attr(escalation, "field_name"),
                    safe_attr(escalation, "field_name"),
                ),
                "Why it needed review": simplify_reason(
                    safe_attr(escalation, "weakness_reason")
                ),
                "First pass": safe_attr(escalation, "current_value"),
                "Final answer": safe_attr(escalation, "final_value"),
                "Outcome": STATUS_LABELS.get(
                    safe_attr(escalation, "final_status"),
                    safe_attr(escalation, "final_status"),
                ),
                "Review action": ACTION_LABELS.get(
                    safe_attr(adjudication, "recommended_action"),
                    safe_attr(adjudication, "recommended_action"),
                )
                if adjudication
                else None,
                "Reason": safe_attr(adjudication, "rationale")
                if adjudication
                else None,
                "Evidence used": "\n\n".join(
                    safe_attr(escalation, "supporting_snippets", []) or []
                ),
            }
        )

    return rows


def display_final_comparison_rows(
    results: list[TargetResearchResult],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for result in results:
        for field_name, final_field in iter_record_fields(result.final_record):
            raw_status = normalize_status(final_field)
            rows.append(
                {
                    "University": result.university_name,
                    "Program": result.program_name,
                    "Degree": result.degree_type,
                    "Requirement": FIELD_LABELS.get(field_name, field_name),
                    "Final answer": safe_attr(final_field, "value"),
                    "Result": STATUS_LABELS.get(raw_status, raw_status),
                    "Source page": safe_attr(final_field, "source_url"),
                }
            )

    return rows


def final_comparison_rows(results: list[TargetResearchResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for result in results:
        for field_name, final_field in iter_record_fields(result.final_record):
            rows.append(
                {
                    "university_name": result.university_name,
                    "program_name": result.program_name,
                    "degree_type": result.degree_type,
                    "field_name": field_name,
                    "final_value": safe_attr(final_field, "value"),
                    "final_status": normalize_status(final_field),
                    "source_url": safe_attr(final_field, "source_url"),
                    "evidence_text": safe_attr(final_field, "evidence_text"),
                }
            )

    return rows


def source_discovery_rows(results: list[TargetResearchResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for result in results:
        source_discovery = safe_attr(result, "source_discovery")
        if not source_discovery:
            continue

        candidates = safe_attr(source_discovery, "candidates", []) or []
        for candidate in candidates:
            rows.append(
                {
                    "university_name": result.university_name,
                    "program_name": result.program_name,
                    "degree_type": result.degree_type,
                    "source_type": safe_attr(candidate, "source_type"),
                    "query": safe_attr(candidate, "query"),
                    "url": safe_attr(candidate, "url"),
                    "title": safe_attr(candidate, "title"),
                    "selected": safe_attr(candidate, "selected"),
                    "is_official": safe_attr(candidate, "is_official"),
                    "confidence": safe_attr(candidate, "confidence"),
                    "reason": safe_attr(candidate, "reason"),
                    "rejection_reason": safe_attr(candidate, "rejection_reason"),
                }
            )

    return rows


def ai_vs_verified_rows(results: list[TargetResearchResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for result in results:
        for field_name, final_field in iter_record_fields(result.final_record):
            generated_value = None
            generated_status = None
            generated_source_url = None

            for page_result in result.page_results:
                extracted = safe_attr(page_result, "extracted")
                extracted_field = safe_attr(extracted, field_name)
                extracted_value = safe_attr(extracted_field, "value")
                if extracted_value:
                    generated_value = extracted_value
                    generated_status = normalize_status(extracted_field)
                    generated_source_url = safe_attr(page_result, "source_url")
                    break

            rows.append(
                {
                    "university_name": result.university_name,
                    "program_name": result.program_name,
                    "degree_type": result.degree_type,
                    "field_name": field_name,
                    "generated_value": generated_value,
                    "generated_status": generated_status,
                    "generated_source_url": generated_source_url,
                    "verified_value": safe_attr(final_field, "value"),
                    "verified_status": normalize_status(final_field),
                    "verified_source_url": safe_attr(final_field, "source_url"),
                }
            )

    return rows


def correction_rows(results: list[TargetResearchResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for result in results:
        for page_result in result.page_results:
            field_escalations = safe_attr(page_result, "field_escalations", []) or []
            for escalation in field_escalations:
                adjudication = safe_attr(escalation, "adjudication")
                rows.append(
                    {
                        "university_name": result.university_name,
                        "program_name": result.program_name,
                        "degree_type": result.degree_type,
                        "field_name": safe_attr(escalation, "field_name"),
                        "source_url": safe_attr(page_result, "source_url"),
                        "initial_value": safe_attr(escalation, "current_value"),
                        "initial_status": safe_attr(escalation, "current_status"),
                        "weakness_reason": safe_attr(escalation, "weakness_reason"),
                        "final_value": safe_attr(escalation, "final_value"),
                        "final_status": safe_attr(escalation, "final_status"),
                        "resolved": bool(safe_attr(escalation, "resolved", False)),
                        "llm_action": safe_attr(adjudication, "recommended_action"),
                        "citation": safe_attr(adjudication, "citation"),
                        "rationale": safe_attr(adjudication, "rationale"),
                    }
                )

    return rows


def field_review_rows(results: list[TargetResearchResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    correction_lookup: dict[tuple[str, str, str | None, str], dict[str, Any]] = {}

    for row in correction_rows(results):
        key = (
            row.get("university_name"),
            row.get("program_name"),
            row.get("degree_type"),
            row.get("field_name"),
        )
        existing = correction_lookup.get(key)
        if existing is None or row.get("resolved"):
            correction_lookup[key] = row

    for row in ai_vs_verified_rows(results):
        key = (
            row.get("university_name"),
            row.get("program_name"),
            row.get("degree_type"),
            row.get("field_name"),
        )
        correction = correction_lookup.get(key)

        final_status = row.get("verified_status")
        generated_value = row.get("generated_value")
        verified_value = row.get("verified_value")

        has_change = generated_value != verified_value or final_status in {
            "corrected",
            "adjudicated",
            "uncertain",
        }
        if not has_change:
            continue

        rows.append(
            {
                "University": row.get("university_name"),
                "Program": row.get("program_name"),
                "Requirement": FIELD_LABELS.get(
                    row.get("field_name"), row.get("field_name")
                ),
                "First pass": generated_value,
                "Final answer": verified_value,
                "Outcome": STATUS_LABELS.get(final_status, final_status),
                "Why": simplify_reason(correction.get("weakness_reason"))
                if correction
                else None,
                "Decision": ACTION_LABELS.get(
                    correction.get("llm_action"), correction.get("llm_action")
                )
                if correction and correction.get("llm_action")
                else None,
            }
        )

    return rows


def has_source_discovery(results: list[TargetResearchResult]) -> bool:
    return any(bool(safe_attr(result, "source_discovery")) for result in results)


def summarise_results(results: list[TargetResearchResult]) -> tuple[int, int, int]:
    total_pages = sum(len(result.page_results) for result in results)
    confirmed_fields = 0
    uncertain_fields = 0

    for result in results:
        for _, final_field in iter_record_fields(result.final_record):
            status = normalize_status(final_field)
            if status in FINAL_OK_STATUSES:
                confirmed_fields += 1
            elif status == "uncertain":
                uncertain_fields += 1

    return total_pages, confirmed_fields, uncertain_fields


def run_and_store_results(targets: list[Any]) -> None:
    runtime = build_runtime_options()
    progress = st.progress(0.0, text="Preparing pipeline run")
    status = st.empty()
    total = max(len(targets), 1)

    def on_progress(stage: str, index: int, count: int, target: Any) -> None:
        progress.progress(
            min(index / count, 1.0),
            text=f"{stage.title()} {index}/{count}: {safe_attr(target, 'university_name', 'Target')}",
        )
        detail = safe_attr(target, "degree_type", None)
        suffix = f" | {detail}" if detail else ""
        status.caption(
            f"{safe_attr(target, 'program_name', 'Unknown program')} | "
            f"{safe_attr(target, 'country', 'Unknown country')}{suffix}"
        )

    results: list[TargetResearchResult] = []
    client_timeout = max(getattr(settings, "default_timeout", 30.0), 120.0)

    try:
        with httpx.Client(timeout=client_timeout) as client:
            for index, target in enumerate(targets, start=1):
                on_progress("run", index, total, target)

                endpoint = (
                    f"{backend_base_url()}/research/run-target"
                    if isinstance(target, ResearchTarget)
                    else f"{backend_base_url()}/research/run"
                )

                payload = {
                    "target": target.model_dump(mode="json"),
                    "runtime": runtime.model_dump(mode="json"),
                }

                response = client.post(endpoint, json=payload)
                response.raise_for_status()

                response_json = response.json()
                data = response_json.get("data")
                if data is None:
                    raise ValueError(
                        "Backend response is missing 'data'. "
                        f"Response keys: {list(response_json.keys())}"
                    )

                results.append(TargetResearchResult.model_validate(data))
                on_progress("complete", index, total, target)

    except httpx.HTTPStatusError as exc:
        body_preview = exc.response.text[:1000] if exc.response is not None else ""
        raise RuntimeError(
            f"Backend returned HTTP {exc.response.status_code} for "
            f"{exc.request.method} {exc.request.url}. Response preview: {body_preview}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Could not reach backend at {backend_base_url()}. Reason: {exc}"
        ) from exc

    export_payloads = build_export_payloads(results)

    progress.progress(1.0, text="Run complete")
    status.caption(f"Received results from backend at {backend_base_url()}")

    st.session_state["results"] = results
    st.session_state["export_payloads"] = export_payloads


def render_results(
    results: list[TargetResearchResult], export_payloads: dict[str, str]
) -> None:
    total_pages, confirmed_fields, uncertain_fields = summarise_results(results)

    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Targets", len(results))
    metric_b.metric("Pages processed", total_pages)
    metric_c.metric("Verified/corrected fields", confirmed_fields)

    if uncertain_fields:
        st.warning(f"{uncertain_fields} final fields are still marked uncertain.")

    final_tab, evidence_tab, exports_tab = st.tabs(
        ["Final Results", "Sources & Evidence", "Exports"]
    )

    with final_tab:
        st.markdown(
            "Final admissions answers first, with one plain-English review table for changed or unclear fields."
        )
        st.dataframe(display_final_comparison_rows(results), use_container_width=True)

        review_rows = field_review_rows(results)
        if review_rows:
            st.subheader("Field Review")
            st.dataframe(review_rows, use_container_width=True)
        elif uncertain_fields:
            st.info(
                "Some fields are still unclear, but no review notes were generated for display."
            )
        else:
            st.caption("No extra review notes were needed for this run.")

    with evidence_tab:
        all_discovery_rows = source_discovery_rows(results)

        for result in results:
            with st.container(border=True):
                st.subheader(f"{result.university_name} | {result.program_name}")
                st.caption(
                    f"{result.country} | {result.degree_type or 'Degree unspecified'} | "
                    f"{len(result.page_results)} source pages"
                )

                st.dataframe(
                    record_to_rows(result.final_record), use_container_width=True
                )

                if result.source_discovery:
                    with st.expander("Source discovery"):
                        discovery_rows = [
                            row
                            for row in all_discovery_rows
                            if row["university_name"] == result.university_name
                            and row["program_name"] == result.program_name
                            and row["degree_type"] == result.degree_type
                        ]
                        if discovery_rows:
                            st.dataframe(discovery_rows, use_container_width=True)
                        else:
                            st.caption(
                                "No discovery rows were available for this target."
                            )

                for page_index, page_result in enumerate(result.page_results, start=1):
                    with st.expander(
                        f"Source {page_index}: {safe_attr(page_result, 'source_type')} | "
                        f"{safe_attr(page_result, 'fetch_mode')}"
                    ):
                        st.json(
                            {
                                "source_url": safe_attr(page_result, "source_url"),
                                "saved_path": safe_attr(page_result, "saved_path"),
                                "title": safe_attr(page_result, "title"),
                                "content_length": safe_attr(
                                    page_result, "content_length"
                                ),
                            }
                        )

                        page_tabs = st.tabs(["Verified", "Extracted", "Escalations"])

                        with page_tabs[0]:
                            verified_record = safe_attr(page_result, "verified")
                            if verified_record:
                                st.dataframe(
                                    record_to_rows(verified_record),
                                    use_container_width=True,
                                )
                            else:
                                st.caption("No verified record available.")

                        with page_tabs[1]:
                            extracted_record = safe_attr(page_result, "extracted")
                            if extracted_record:
                                st.dataframe(
                                    record_to_rows(extracted_record),
                                    use_container_width=True,
                                )
                            else:
                                st.caption("No extracted record available.")

                        with page_tabs[2]:
                            escalations = (
                                safe_attr(page_result, "field_escalations", []) or []
                            )
                            if escalations:
                                st.dataframe(
                                    escalation_to_rows(escalations),
                                    use_container_width=True,
                                )
                            else:
                                st.caption(
                                    "No adjudication was needed for this source page."
                                )

        if not has_source_discovery(results):
            st.caption(
                "Source discovery is hidden for manual runs unless discovery data exists."
            )

    with exports_tab:
        export_columns = st.columns(3)

        target_results_json = export_payloads.get("target_results")
        final_records_json = export_payloads.get("final_records")
        comparison_csv_text = export_payloads.get("comparison_csv")
        ai_vs_verified_csv = export_payloads.get("ai_vs_verified")
        correction_log_csv = export_payloads.get("correction_log")
        source_discovery_json = export_payloads.get("source_discovery")

        if target_results_json:
            export_columns[0].download_button(
                "Download target results JSON",
                data=target_results_json,
                file_name="target_results.json",
                mime="application/json",
                use_container_width=True,
            )

        if final_records_json:
            export_columns[1].download_button(
                "Download final records JSON",
                data=final_records_json,
                file_name="final_records.json",
                mime="application/json",
                use_container_width=True,
            )

        if comparison_csv_text:
            export_columns[2].download_button(
                "Download comparison CSV",
                data=comparison_csv_text,
                file_name="comparison_table.csv",
                mime="text/csv",
                use_container_width=True,
            )

        extra_export_columns = st.columns(3)

        if source_discovery_json and has_source_discovery(results):
            extra_export_columns[0].download_button(
                "Download source discovery JSON",
                data=source_discovery_json,
                file_name="source_discovery.json",
                mime="application/json",
                use_container_width=True,
            )

        if ai_vs_verified_csv:
            extra_export_columns[1].download_button(
                "Download AI vs verified CSV",
                data=ai_vs_verified_csv,
                file_name="ai_vs_verified.csv",
                mime="text/csv",
                use_container_width=True,
            )

        if correction_log_csv:
            extra_export_columns[2].download_button(
                "Download correction log CSV",
                data=correction_log_csv,
                file_name="correction_log.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.caption(
            "Input intent or manual URLs -> optional discovery -> fetch -> extract -> verify -> adjudicate -> merge"
        )
        with st.expander("Workflow notes"):
            st.markdown(
                """
                This workflow is structured as a reusable research operator pipeline:

                - official pages remain the source of truth
                - weak fields are adjudicated instead of silently accepted
                - exports preserve evidence, comparison, and correction artifacts
                """
            )


def init_page() -> None:
    st.set_page_config(
        page_title="Callus Admissions Research",
        page_icon="C",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(198, 223, 255, 0.55), transparent 32%),
                linear-gradient(180deg, #f7f4ec 0%, #eef3f8 100%);
        }
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            backdrop-filter: blur(10px);
        }
        div[data-testid="stVerticalBlock"] div[data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.subheader("Runtime")

        st.text_input(
            "Backend API URL",
            key="ui_backend_base_url",
            help="FastAPI base URL used by the Streamlit frontend.",
        )

        st.selectbox(
            "LLM provider",
            options=LLM_PROVIDERS,
            key="ui_llm_provider",
        )

        st.text_input(
            "LLM model",
            key="ui_llm_model",
            help="Used by the selected LLM provider, including Hugging Face inference.",
        )

        if st.session_state["ui_llm_provider"] == "hf_inference":
            st.text_input(
                "HF token",
                key="ui_hf_token",
                type="password",
                help="Optional runtime override for HF_TOKEN.",
            )

        st.selectbox(
            "Discovery provider",
            options=DISCOVERY_PROVIDERS,
            key="ui_discovery_provider",
        )

        if st.session_state["ui_discovery_provider"] == MANUAL_DISCOVERY_PROVIDER:
            st.caption("Manual mode bypasses discovery and uses your URLs directly.")
        elif st.session_state["ui_discovery_provider"] == "adk_google_search":
            st.text_input(
                "Discovery model",
                key="ui_discovery_model",
                help="Used by the ADK Google Search discovery agent.",
            )
        elif st.session_state["ui_discovery_provider"] == "google_custom_search":
            st.text_input(
                "Search engine ID",
                key="ui_google_search_engine_id",
                help="Programmable Search Engine ID (cx) for Google Custom Search.",
            )
            st.text_input(
                "Search API key",
                key="ui_google_search_api_key",
                type="password",
                help="Optional override for GOOGLE_SEARCH_API_KEY.",
            )
        else:
            st.text_input(
                "Vertex project ID",
                key="ui_vertex_search_project_id",
                help="Google Cloud project that owns the Vertex AI Search data store.",
            )
            st.text_input(
                "Vertex location",
                key="ui_vertex_search_location",
                help="Usually global, us, or eu.",
            )
            st.text_input(
                "Data store ID",
                key="ui_vertex_search_data_store_id",
                help="Vertex AI Search data store ID from the console.",
            )
            st.text_input(
                "Serving config ID",
                key="ui_vertex_search_serving_config_id",
                help="Usually default_config.",
            )
            st.text_input(
                "Service account JSON path",
                key="ui_vertex_search_credentials_path",
                help="Optional local path. Leave blank to use ADC credentials.",
            )

        st.caption(
            "Runtime settings are sent to the backend for the next workflow run."
        )


def render_input_tab() -> None:
    st.markdown("Run a single research workflow from either discovery or manual URLs.")
    left, right = st.columns([0.9, 1.1])

    with left:
        university_name = st.text_input(
            "University name",
            placeholder="Stanford University",
        )
        country = st.text_input("Country", placeholder="US")
        program_name = st.text_input(
            "Program name",
            placeholder="MS Computer Science",
        )
        degree_type = st.selectbox("Degree type", DEGREE_TYPES, index=0)

    with right:
        if st.session_state["ui_discovery_provider"] != MANUAL_DISCOVERY_PROVIDER:
            st.markdown(
                """
                The app automatically discovers and ranks official source pages for:

                - program page
                - admissions requirements
                - English requirements
                - application fee
                """
            )
        else:
            st.markdown(
                """
                Manual mode bypasses discovery and sends your URLs straight into the
                fetch, extract, verify, and adjudication pipeline.

                Use one URL per line, or:

                - `url | source_type`
                - `url | source_type | mode`
                """
            )
            st.selectbox(
                "Default source type",
                options=SOURCE_TYPES,
                key="ui_manual_source_type",
                help="Applied to manual lines that do not include a source type.",
            )
            st.selectbox(
                "Default fetch mode",
                options=FETCH_MODES,
                key="ui_manual_fetch_mode",
                help="Applied to manual lines that do not include a fetch mode.",
            )

    if st.session_state["ui_discovery_provider"] == MANUAL_DISCOVERY_PROVIDER:
        st.text_area(
            "Manual source URLs",
            key="ui_manual_source_urls",
            height=180,
            placeholder=(
                "https://cs.stanford.edu/admissions/masters\n"
                "https://gradadmissions.stanford.edu/applying/fees | fee_page\n"
                "https://gradadmissions.stanford.edu/applying/international | "
                "english_requirements_page | browser"
            ),
            help=(
                "Manual fallback for cases where discovery is blocked by provider "
                "quota, credentials, or ranking misses."
            ),
        )

    if st.button("Run workflow", type="primary", use_container_width=True):
        try:
            if st.session_state["ui_discovery_provider"] != MANUAL_DISCOVERY_PROVIDER:
                target = build_intent_from_form(
                    university_name=university_name,
                    country=country,
                    program_name=program_name,
                    degree_type=degree_type,
                )
            else:
                target = build_manual_target_from_form(
                    university_name=university_name,
                    country=country,
                    program_name=program_name,
                    degree_type=degree_type,
                    source_urls_text=st.session_state["ui_manual_source_urls"],
                    default_source_type=st.session_state["ui_manual_source_type"],
                    default_fetch_mode=st.session_state["ui_manual_fetch_mode"],
                )

            run_and_store_results([target])

        except ValidationError as exc:
            st.error(str(exc))
        except ValueError as exc:
            st.error(str(exc))
        except RuntimeError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.exception(exc)


def render_review_tab() -> None:
    results = st.session_state["results"]
    if not results:
        st.info("No run results yet. Start from Configure & Run.")
        return

    export_payloads = st.session_state["export_payloads"]
    render_results(results, export_payloads)


def main() -> None:
    init_page()
    init_session_state()

    st.title("Callus Admissions Research")
    st.caption(
        f"Research pipeline UI for {settings.app_name}. Data directory: {settings.data_dir}"
    )

    render_sidebar()

    input_tab, review_tab = st.tabs(["Configure & Run", "Results"])

    with input_tab:
        render_input_tab()

    with review_tab:
        render_review_tab()


if __name__ == "__main__":
    main()
