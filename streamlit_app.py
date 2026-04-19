from __future__ import annotations

import sys
import json
from io import StringIO
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st
import httpx
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


def apply_runtime_settings() -> None:
    return None


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
        vertex_search_data_store_id=st.session_state["ui_vertex_search_data_store_id"].strip()
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

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def build_export_payloads(results: list[TargetResearchResult]) -> dict[str, str]:
    return {
        "target_results": json.dumps(
            [result.model_dump(mode="json") for result in results], indent=2
        ),
        "final_records": json.dumps(
            [result.final_record.model_dump(mode="json") for result in results], indent=2
        ),
        "comparison_csv": csv_text(final_comparison_rows(results)),
        "source_discovery": json.dumps(source_discovery_rows(results), indent=2),
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
                "or 'url | source_type | mode'. "
                f"Problem on line {line_number}."
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
        source_urls_text,
        default_source_type,
        default_fetch_mode,
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


def record_to_rows(record: Any) -> list[dict[str, str | None]]:
    return [
        {
            "field": "application_deadline",
            "value": record.application_deadline.value,
            "status": record.application_deadline.status,
            "source_url": record.application_deadline.source_url,
            "evidence_text": record.application_deadline.evidence_text,
        },
        {
            "field": "english_proficiency",
            "value": record.english_proficiency.value,
            "status": record.english_proficiency.status,
            "source_url": record.english_proficiency.source_url,
            "evidence_text": record.english_proficiency.evidence_text,
        },
        {
            "field": "application_fee",
            "value": record.application_fee.value,
            "status": record.application_fee.status,
            "source_url": record.application_fee.source_url,
            "evidence_text": record.application_fee.evidence_text,
        },
        {
            "field": "notable_requirement",
            "value": record.notable_requirement.value,
            "status": record.notable_requirement.status,
            "source_url": record.notable_requirement.source_url,
            "evidence_text": record.notable_requirement.evidence_text,
        },
    ]


def escalation_to_rows(field_escalations: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for escalation in field_escalations:
        adjudication = escalation.adjudication
        rows.append(
            {
                "field": escalation.field_name,
                "weakness_reason": escalation.weakness_reason,
                "current_status": escalation.current_status,
                "current_value": escalation.current_value,
                "resolved": escalation.resolved,
                "final_status": escalation.final_status,
                "final_value": escalation.final_value,
                "llm_action": adjudication.recommended_action if adjudication else None,
                "llm_confidence": adjudication.confidence if adjudication else None,
                "citation_type": adjudication.citation_type if adjudication else None,
                "citation": adjudication.citation if adjudication else None,
                "rationale": adjudication.rationale if adjudication else None,
                "supporting_snippets": "\n\n".join(escalation.supporting_snippets),
            }
        )
    return rows


def source_discovery_rows(results: list[TargetResearchResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        if not result.source_discovery:
            continue
        for candidate in result.source_discovery.candidates:
            rows.append(
                {
                    "university_name": result.university_name,
                    "program_name": result.program_name,
                    "degree_type": result.degree_type,
                    "source_type": candidate.source_type,
                    "query": candidate.query,
                    "url": candidate.url,
                    "title": candidate.title,
                    "selected": candidate.selected,
                    "is_official": candidate.is_official,
                    "confidence": candidate.confidence,
                    "reason": candidate.reason,
                    "rejection_reason": candidate.rejection_reason,
                }
            )
    return rows


def final_comparison_rows(results: list[TargetResearchResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fields = [
        "application_deadline",
        "english_proficiency",
        "application_fee",
        "notable_requirement",
    ]
    for result in results:
        for field_name in fields:
            final_field = getattr(result.final_record, field_name)
            rows.append(
                {
                    "university_name": result.university_name,
                    "program_name": result.program_name,
                    "degree_type": result.degree_type,
                    "field_name": field_name,
                    "final_value": final_field.value,
                    "final_status": final_field.status,
                    "source_url": final_field.source_url,
                    "evidence_text": final_field.evidence_text,
                }
            )
    return rows


def ai_vs_verified_rows(results: list[TargetResearchResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fields = [
        "application_deadline",
        "english_proficiency",
        "application_fee",
        "notable_requirement",
    ]
    for result in results:
        for field_name in fields:
            generated_value = None
            generated_status = None
            generated_source_url = None
            for page_result in result.page_results:
                extracted_field = getattr(page_result.extracted, field_name)
                if extracted_field.value:
                    generated_value = extracted_field.value
                    generated_status = extracted_field.status
                    generated_source_url = page_result.source_url
                    break

            final_field = getattr(result.final_record, field_name)
            rows.append(
                {
                    "university_name": result.university_name,
                    "program_name": result.program_name,
                    "degree_type": result.degree_type,
                    "field_name": field_name,
                    "generated_value": generated_value,
                    "generated_status": generated_status,
                    "generated_source_url": generated_source_url,
                    "verified_value": final_field.value,
                    "verified_status": final_field.status,
                    "verified_source_url": final_field.source_url,
                }
            )
    return rows


def correction_rows(results: list[TargetResearchResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        for page_result in result.page_results:
            for escalation in page_result.field_escalations:
                adjudication = escalation.adjudication
                rows.append(
                    {
                        "university_name": result.university_name,
                        "program_name": result.program_name,
                        "degree_type": result.degree_type,
                        "field_name": escalation.field_name,
                        "source_url": page_result.source_url,
                        "initial_value": escalation.current_value,
                        "initial_status": escalation.current_status,
                        "weakness_reason": escalation.weakness_reason,
                        "final_value": escalation.final_value,
                        "final_status": escalation.final_status,
                        "resolved": escalation.resolved,
                        "llm_action": adjudication.recommended_action
                        if adjudication
                        else None,
                        "citation": adjudication.citation if adjudication else None,
                        "rationale": adjudication.rationale if adjudication else None,
                    }
                )
    return rows


def correction_highlight_rows(results: list[TargetResearchResult]) -> list[dict[str, Any]]:
    highlights: list[dict[str, Any]] = []
    for row in correction_rows(results):
        if row["resolved"] or row["final_status"] == "uncertain":
            highlights.append(
                {
                    "university_name": row["university_name"],
                    "program_name": row["program_name"],
                    "field_name": row["field_name"],
                    "initial_status": row["initial_status"],
                    "final_status": row["final_status"],
                    "weakness_reason": row["weakness_reason"],
                    "llm_action": row["llm_action"],
                    "rationale": row["rationale"],
                }
            )
    return highlights


def has_source_discovery(results: list[TargetResearchResult]) -> bool:
    return any(result.source_discovery for result in results)


def summarise_results(results: list[TargetResearchResult]) -> tuple[int, int, int]:
    total_pages = sum(len(result.page_results) for result in results)
    corrected_or_verified = 0
    uncertain = 0
    for result in results:
        for field in record_to_rows(result.final_record):
            if field["status"] in {"verified", "corrected", "adjudicated"}:
                corrected_or_verified += 1
            if field["status"] == "uncertain":
                uncertain += 1
    return total_pages, corrected_or_verified, uncertain


def run_and_store_results(targets: list[Any]) -> None:
    runtime = build_runtime_options()
    progress = st.progress(0.0, text="Preparing pipeline run")
    status = st.empty()
    total = max(len(targets), 1)

    def on_progress(stage: str, index: int, count: int, target: Any) -> None:
        progress.progress(
            min(index / count, 1.0),
            text=f"{stage.title()} {index}/{count}: {target.university_name}",
        )
        detail = getattr(target, "degree_type", None)
        suffix = f" | {detail}" if detail else ""
        status.caption(f"{target.program_name} | {target.country}{suffix}")

    results: list[TargetResearchResult] = []
    client_timeout = max(settings.default_timeout, 120.0)
    with httpx.Client(timeout=client_timeout) as client:
        for index, target in enumerate(targets, start=1):
            on_progress("run", index, total, target)
            if isinstance(target, ResearchTarget):
                endpoint = f"{backend_base_url()}/research/run-target"
            else:
                endpoint = f"{backend_base_url()}/research/run"
            response = client.post(
                endpoint,
                json={
                    "target": target.model_dump(mode="json"),
                    "runtime": runtime.model_dump(mode="json"),
                },
            )
            response.raise_for_status()
            payload = response.json()
            results.append(TargetResearchResult.model_validate(payload["data"]))
            on_progress("complete", index, total, target)

    export_payloads = build_export_payloads(results)

    progress.progress(1.0, text="Run complete")
    status.caption(f"Received results from backend at {backend_base_url()}")

    st.session_state["results"] = results
    st.session_state["export_payloads"] = export_payloads


def render_results(results: list[TargetResearchResult], export_payloads: dict[str, str]) -> None:
    total_pages, confirmed_fields, uncertain_fields = summarise_results(results)
    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Targets", len(results))
    metric_b.metric("Pages processed", total_pages)
    metric_c.metric("Verified/corrected fields", confirmed_fields)
    if uncertain_fields:
        st.warning(f"{uncertain_fields} final fields are still marked uncertain.")

    final_tab, evidence_tab, exports_tab = st.tabs(
        [
            "Final Results",
            "Sources & Evidence",
            "Exports",
        ]
    )

    with final_tab:
        st.markdown("Verified admissions results with validation and exception highlights.")
        st.dataframe(final_comparison_rows(results), width="stretch")
        with st.expander("Validation"):
            st.dataframe(ai_vs_verified_rows(results), width="stretch")
        highlight_rows = correction_highlight_rows(results)
        if highlight_rows:
            st.subheader("Correction Highlights")
            st.dataframe(highlight_rows, width="stretch")
        elif uncertain_fields:
            st.info("No corrected fields were produced. Remaining weak fields stayed unresolved.")
        else:
            st.caption("No correction highlights were needed for this run.")

    with evidence_tab:
        for result in results:
            with st.container(border=True):
                st.subheader(f"{result.university_name} | {result.program_name}")
                st.caption(
                    f"{result.country} | {result.degree_type or 'Degree unspecified'} | "
                    f"{len(result.page_results)} source pages"
                )
                st.dataframe(record_to_rows(result.final_record), width="stretch")
                if result.source_discovery:
                    with st.expander("Source discovery"):
                        discovery_rows = [
                            row
                            for row in source_discovery_rows(results)
                            if row["university_name"] == result.university_name
                            and row["program_name"] == result.program_name
                            and row["degree_type"] == result.degree_type
                        ]
                        st.dataframe(discovery_rows, width="stretch")
                for page_index, page_result in enumerate(result.page_results, start=1):
                    with st.expander(
                        f"Source {page_index}: {page_result.source_type} | {page_result.fetch_mode}"
                    ):
                        st.write(
                            {
                                "source_url": page_result.source_url,
                                "saved_path": page_result.saved_path,
                                "title": page_result.title,
                                "content_length": page_result.content_length,
                            }
                        )
                        page_tabs = st.tabs(["Verified", "Extracted", "Escalations"])
                        with page_tabs[0]:
                            st.dataframe(
                                record_to_rows(page_result.verified),
                                width="stretch",
                            )
                        with page_tabs[1]:
                            st.dataframe(
                                record_to_rows(page_result.extracted),
                                width="stretch",
                            )
                        with page_tabs[2]:
                            if page_result.field_escalations:
                                st.dataframe(
                                    escalation_to_rows(page_result.field_escalations),
                                    width="stretch",
                                )
                            else:
                                st.caption(
                                    "No adjudication was needed for this source page."
                                )
        if not has_source_discovery(results):
            st.caption("Source discovery is hidden for manual runs unless discovery data exists.")

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
                width="stretch",
            )
        if final_records_json:
            export_columns[1].download_button(
                "Download final records JSON",
                data=final_records_json,
                file_name="final_records.json",
                mime="application/json",
                width="stretch",
            )
        if comparison_csv_text:
            export_columns[2].download_button(
                "Download comparison CSV",
                data=comparison_csv_text,
                file_name="comparison_table.csv",
                mime="text/csv",
                width="stretch",
            )

        extra_export_columns = st.columns(3)
        if source_discovery_json and has_source_discovery(results):
            extra_export_columns[0].download_button(
                "Download source discovery JSON",
                data=source_discovery_json,
                file_name="source_discovery.json",
                mime="application/json",
                width="stretch",
            )
        if ai_vs_verified_csv:
            extra_export_columns[1].download_button(
                "Download AI vs verified CSV",
                data=ai_vs_verified_csv,
                file_name="ai_vs_verified.csv",
                mime="text/csv",
                width="stretch",
            )
        if correction_log_csv:
            extra_export_columns[2].download_button(
                "Download correction log CSV",
                data=correction_log_csv,
                file_name="correction_log.csv",
                mime="text/csv",
                width="stretch",
            )

        st.caption("Input intent or manual URLs -> optional discovery -> fetch -> extract -> verify -> adjudicate -> merge")
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


def main() -> None:
    init_page()

    if "results" not in st.session_state:
        st.session_state["results"] = []
    if "export_payloads" not in st.session_state:
        st.session_state["export_payloads"] = {}
    if "ui_backend_base_url" not in st.session_state:
        st.session_state["ui_backend_base_url"] = "http://127.0.0.1:8000"
    if "ui_llm_provider" not in st.session_state:
        st.session_state["ui_llm_provider"] = settings.llm_provider
    if "ui_llm_model" not in st.session_state:
        st.session_state["ui_llm_model"] = settings.llm_model
    if "ui_discovery_provider" not in st.session_state:
        st.session_state["ui_discovery_provider"] = settings.discovery_provider
    if "ui_discovery_model" not in st.session_state:
        st.session_state["ui_discovery_model"] = settings.discovery_model
    if "ui_hf_token" not in st.session_state:
        st.session_state["ui_hf_token"] = settings.hf_token or ""
    if "ui_google_search_api_key" not in st.session_state:
        st.session_state["ui_google_search_api_key"] = ""
    if "ui_google_search_engine_id" not in st.session_state:
        st.session_state["ui_google_search_engine_id"] = (
            settings.google_search_engine_id or ""
        )
    if "ui_vertex_search_project_id" not in st.session_state:
        st.session_state["ui_vertex_search_project_id"] = (
            settings.vertex_search_project_id or ""
        )
    if "ui_vertex_search_location" not in st.session_state:
        st.session_state["ui_vertex_search_location"] = (
            settings.vertex_search_location or "global"
        )
    if "ui_vertex_search_data_store_id" not in st.session_state:
        st.session_state["ui_vertex_search_data_store_id"] = (
            settings.vertex_search_data_store_id or ""
        )
    if "ui_vertex_search_serving_config_id" not in st.session_state:
        st.session_state["ui_vertex_search_serving_config_id"] = (
            settings.vertex_search_serving_config_id or "default_config"
        )
    if "ui_vertex_search_credentials_path" not in st.session_state:
        st.session_state["ui_vertex_search_credentials_path"] = (
            settings.vertex_search_credentials_path or ""
        )
    if "ui_manual_source_urls" not in st.session_state:
        st.session_state["ui_manual_source_urls"] = ""
    if "ui_manual_source_type" not in st.session_state:
        st.session_state["ui_manual_source_type"] = "program_page"
    if "ui_manual_fetch_mode" not in st.session_state:
        st.session_state["ui_manual_fetch_mode"] = "auto"

    st.title("Callus Admissions Research")
    st.caption(
        f"Research pipeline UI for {settings.app_name}. Data directory: {settings.data_dir}"
    )

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
        st.caption("Runtime settings are sent to the backend for the next workflow run.")

    input_tab, review_tab = st.tabs(["Configure & Run", "Results"])

    with input_tab:
        st.markdown(
            "Run a single research workflow from either discovery or manual URLs."
        )
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

        if st.button("Run workflow", type="primary", width="stretch"):
            try:
                if (
                    st.session_state["ui_discovery_provider"]
                    != MANUAL_DISCOVERY_PROVIDER
                ):
                    target = build_intent_from_form(
                        university_name,
                        country,
                        program_name,
                        degree_type,
                    )
                else:
                    target = build_manual_target_from_form(
                        university_name,
                        country,
                        program_name,
                        degree_type,
                        st.session_state["ui_manual_source_urls"],
                        st.session_state["ui_manual_source_type"],
                        st.session_state["ui_manual_fetch_mode"],
                    )
                run_and_store_results([target])
            except ValidationError as exc:
                st.error(exc)
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.exception(exc)

    with review_tab:
        results = st.session_state["results"]
        if not results:
            st.info("No run results yet. Start from Configure & Run.")
        else:
            export_payloads = st.session_state["export_payloads"]
            render_results(results, export_payloads)


if __name__ == "__main__":
    main()
