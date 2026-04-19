from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st
from pydantic import ValidationError

from callus_research.config import settings
from callus_research.models.research_result import TargetResearchResult
from callus_research.models.source_bundle import ResearchIntent
from callus_research.services.batch_runner import (
    export_results_bundle,
    run_targets_sync,
)

DEGREE_TYPES = ["Master's", "PhD", "Bachelor's", "MPhil", "Other"]
LLM_PROVIDERS = ["openai", "gemini", "hf_inference"]
DISCOVERY_PROVIDERS = [
    "adk_google_search",
    "google_custom_search",
    "vertex_ai_search",
]


def apply_runtime_settings() -> None:
    settings.llm_provider = st.session_state["ui_llm_provider"]
    settings.llm_model = st.session_state["ui_llm_model"].strip()
    settings.discovery_provider = st.session_state["ui_discovery_provider"]
    settings.discovery_model = st.session_state["ui_discovery_model"].strip()
    google_search_api_key = st.session_state["ui_google_search_api_key"].strip()
    google_search_engine_id = st.session_state["ui_google_search_engine_id"].strip()
    vertex_search_project_id = st.session_state["ui_vertex_search_project_id"].strip()
    vertex_search_location = st.session_state["ui_vertex_search_location"].strip()
    vertex_search_data_store_id = st.session_state["ui_vertex_search_data_store_id"].strip()
    vertex_search_serving_config_id = st.session_state[
        "ui_vertex_search_serving_config_id"
    ].strip()
    vertex_search_credentials_path = st.session_state[
        "ui_vertex_search_credentials_path"
    ].strip()
    hf_token = st.session_state["ui_hf_token"].strip()
    settings.hf_model_id = settings.llm_model or None
    settings.hf_token = hf_token or None
    settings.google_search_api_key = google_search_api_key or None
    settings.google_search_engine_id = google_search_engine_id or None
    settings.vertex_search_project_id = vertex_search_project_id or None
    settings.vertex_search_location = vertex_search_location or "global"
    settings.vertex_search_data_store_id = vertex_search_data_store_id or None
    settings.vertex_search_serving_config_id = (
        vertex_search_serving_config_id or "default_config"
    )
    settings.vertex_search_credentials_path = vertex_search_credentials_path or None


def build_target_from_form(
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
    apply_runtime_settings()
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

    results = run_targets_sync(targets, progress_callback=on_progress)
    export_paths = export_results_bundle(results)

    progress.progress(1.0, text="Run complete")
    status.caption(f"Saved outputs to {settings.data_dir / 'outputs'}")

    st.session_state["results"] = results
    st.session_state["export_paths"] = export_paths


def render_results(results: list[TargetResearchResult]) -> None:
    total_pages, confirmed_fields, uncertain_fields = summarise_results(results)
    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Targets", len(results))
    metric_b.metric("Pages processed", total_pages)
    metric_c.metric("Verified/corrected fields", confirmed_fields)
    if uncertain_fields:
        st.warning(f"{uncertain_fields} final fields are still marked uncertain.")

    workflow_tab, discovery_tab, comparison_tab, ai_tab, corrections_tab, scale_tab = (
        st.tabs(
            [
                "Workflow",
                "Source Discovery",
                "Final Comparison",
                "AI vs Verified",
                "Corrections",
                "Scaling Note",
            ]
        )
    )

    with workflow_tab:
        st.markdown(
            """
            Input intent -> ADK Google Search discovery -> official URL selection -> fetch ->
            extract -> verify -> targeted LLM adjudication -> merge -> export
            """
        )
        for result in results:
            with st.container(border=True):
                st.subheader(f"{result.university_name} | {result.program_name}")
                st.caption(
                    f"{result.country} | {result.degree_type or 'Degree unspecified'} | "
                    f"{len(result.page_results)} source pages"
                )
                st.dataframe(record_to_rows(result.final_record), use_container_width=True)
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
                                use_container_width=True,
                            )
                        with page_tabs[1]:
                            st.dataframe(
                                record_to_rows(page_result.extracted),
                                use_container_width=True,
                            )
                        with page_tabs[2]:
                            if page_result.field_escalations:
                                st.dataframe(
                                    escalation_to_rows(page_result.field_escalations),
                                    use_container_width=True,
                                )
                            else:
                                st.caption("No adjudication was needed for this source page.")

    with discovery_tab:
        rows = source_discovery_rows(results)
        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("No source discovery trace was captured for these results.")

    with comparison_tab:
        st.dataframe(final_comparison_rows(results), use_container_width=True)

    with ai_tab:
        st.dataframe(ai_vs_verified_rows(results), use_container_width=True)

    with corrections_tab:
        rows = correction_rows(results)
        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("No correction cases were logged for these results.")

    with scale_tab:
        st.markdown(
            """
            This workflow is structured as a reusable research operator pipeline:

            - discovery is isolated behind a provider boundary
            - official pages are stored and used as source of truth
            - weak fields are adjudicated instead of silently accepted
            - exports capture discovery, comparison, and correction artifacts for reuse
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
    if "export_paths" not in st.session_state:
        st.session_state["export_paths"] = {}
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

    st.title("Callus Admissions Research")
    st.caption(
        f"Research pipeline UI for {settings.app_name}. Data directory: {settings.data_dir}"
    )

    with st.sidebar:
        st.subheader("Runtime")
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
        if st.session_state["ui_discovery_provider"] == "adk_google_search":
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
        apply_runtime_settings()
        st.caption("Runtime settings apply to the next workflow run.")

    input_tab, review_tab = st.tabs(["Configure & Run", "Results"])

    with input_tab:
        st.markdown(
            "Run a single research workflow from a program-specific intent."
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
            st.markdown(
                """
                The app automatically discovers and ranks official source pages for:

                - program page
                - admissions requirements
                - English requirements
                - application fee
                """
            )

        if st.button("Run workflow", type="primary", use_container_width=True):
            try:
                target = build_target_from_form(
                    university_name,
                    country,
                    program_name,
                    degree_type,
                )
                run_and_store_results([target])
            except ValidationError as exc:
                st.error(exc)
            except Exception as exc:
                st.exception(exc)

    with review_tab:
        results = st.session_state["results"]
        if not results:
            st.info("No run results yet. Start from Configure & Run.")
        else:
            export_paths = st.session_state["export_paths"]
            export_columns = st.columns(3)
            target_results_path = export_paths.get("target_results")
            final_records_path = export_paths.get("final_records")
            comparison_csv_path = export_paths.get("comparison_csv")
            ai_vs_verified_path = export_paths.get("ai_vs_verified")
            correction_log_path = export_paths.get("correction_log")
            source_discovery_path = export_paths.get("source_discovery")
            if target_results_path:
                export_columns[0].download_button(
                    "Download target results JSON",
                    data=Path(target_results_path).read_text(encoding="utf-8"),
                    file_name=Path(target_results_path).name,
                    mime="application/json",
                    use_container_width=True,
                )
            if final_records_path:
                export_columns[1].download_button(
                    "Download final records JSON",
                    data=Path(final_records_path).read_text(encoding="utf-8"),
                    file_name=Path(final_records_path).name,
                    mime="application/json",
                    use_container_width=True,
                )
            if comparison_csv_path:
                export_columns[2].download_button(
                    "Download comparison CSV",
                    data=Path(comparison_csv_path).read_text(encoding="utf-8"),
                    file_name=Path(comparison_csv_path).name,
                    mime="text/csv",
                    use_container_width=True,
                )

            extra_export_columns = st.columns(3)
            if source_discovery_path:
                extra_export_columns[0].download_button(
                    "Download source discovery JSON",
                    data=Path(source_discovery_path).read_text(encoding="utf-8"),
                    file_name=Path(source_discovery_path).name,
                    mime="application/json",
                    use_container_width=True,
                )
            if ai_vs_verified_path:
                extra_export_columns[1].download_button(
                    "Download AI vs verified CSV",
                    data=Path(ai_vs_verified_path).read_text(encoding="utf-8"),
                    file_name=Path(ai_vs_verified_path).name,
                    mime="text/csv",
                    use_container_width=True,
                )
            if correction_log_path:
                extra_export_columns[2].download_button(
                    "Download correction log CSV",
                    data=Path(correction_log_path).read_text(encoding="utf-8"),
                    file_name=Path(correction_log_path).name,
                    mime="text/csv",
                    use_container_width=True,
                )

            render_results(results)


if __name__ == "__main__":
    main()
