from __future__ import annotations

import json
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
from callus_research.models.source_bundle import ResearchTarget
from callus_research.services.batch_runner import (
    DEFAULT_INPUT_FILE,
    export_results_bundle,
    parse_targets_json,
    run_targets_sync,
    serialize_targets,
)

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
DEFAULT_SOURCE_ROWS = [
    {
        "url": "",
        "source_type": "admissions_page",
        "mode": "auto",
    }
]


def load_input_text() -> str:
    if DEFAULT_INPUT_FILE.exists():
        return DEFAULT_INPUT_FILE.read_text(encoding="utf-8")
    return "[]"


def normalise_rows(rows: Any) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if hasattr(rows, "to_dict"):
        return rows.to_dict(orient="records")
    if isinstance(rows, list):
        return rows
    if isinstance(rows, dict):
        keys = list(rows.keys())
        if not keys:
            return []
        row_count = len(rows[keys[0]])
        return [
            {key: rows[key][index] for key in keys}
            for index in range(row_count)
        ]
    return list(rows)


def build_target_from_form(
    university_name: str,
    country: str,
    program_name: str,
    source_rows: list[dict[str, Any]],
) -> ResearchTarget:
    cleaned_sources = []
    for row in source_rows:
        url = str(row.get("url", "")).strip()
        if not url:
            continue
        cleaned_sources.append(
            {
                "url": url,
                "source_type": row.get("source_type") or "other",
                "mode": row.get("mode") or "auto",
            }
        )

    return ResearchTarget.model_validate(
        {
            "university_name": university_name.strip(),
            "country": country.strip(),
            "program_name": program_name.strip(),
            "sources": cleaned_sources,
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


def run_and_store_results(targets: list[ResearchTarget]) -> None:
    progress = st.progress(0.0, text="Preparing pipeline run")
    status = st.empty()
    total = max(len(targets), 1)

    def on_progress(index: int, count: int, target: ResearchTarget) -> None:
        progress.progress(
            min(index / count, 1.0),
            text=f"Processing {index}/{count}: {target.university_name}",
        )
        status.caption(f"{target.program_name} | {target.country}")

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

    for result in results:
        with st.container(border=True):
            st.subheader(f"{result.university_name} | {result.program_name}")
            st.caption(f"{result.country} | {len(result.page_results)} source pages")
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
                    page_tabs = st.tabs(["Verified", "Extracted"])
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
                    if page_result.field_escalations:
                        st.markdown("Escalations")
                        st.dataframe(
                            escalation_to_rows(page_result.field_escalations),
                            use_container_width=True,
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

    if "batch_json" not in st.session_state:
        st.session_state["batch_json"] = load_input_text()
    if "results" not in st.session_state:
        st.session_state["results"] = []
    if "export_paths" not in st.session_state:
        st.session_state["export_paths"] = {}

    st.title("Callus Admissions Research")
    st.caption(
        f"Research pipeline UI for {settings.app_name}. Data directory: {settings.data_dir}"
    )

    with st.sidebar:
        st.subheader("Runtime")
        st.write(
            {
                "llm_provider": settings.llm_provider,
                "llm_model": settings.llm_model,
                "default_timeout": settings.default_timeout,
                "input_file": str(DEFAULT_INPUT_FILE),
            }
        )
        if st.button("Reload input file", use_container_width=True):
            st.session_state["batch_json"] = load_input_text()
            st.rerun()

    input_tab, review_tab = st.tabs(["Configure & Run", "Results"])

    with input_tab:
        st.markdown(
            "Use the single-target form for quick runs or edit the batch JSON to process multiple universities."
        )
        single_tab, batch_tab = st.tabs(["Single Target", "Batch JSON"])

        with single_tab:
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
            with right:
                source_rows = st.data_editor(
                    DEFAULT_SOURCE_ROWS,
                    num_rows="dynamic",
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "url": st.column_config.TextColumn("Source URL", required=True),
                        "source_type": st.column_config.SelectboxColumn(
                            "Source type",
                            options=SOURCE_TYPES,
                            required=True,
                        ),
                        "mode": st.column_config.SelectboxColumn(
                            "Fetch mode",
                            options=FETCH_MODES,
                            required=True,
                        ),
                    },
                    key="single_target_sources_editor",
                )

            action_a, action_b = st.columns([0.6, 0.4])
            with action_a:
                if st.button("Run single target", type="primary", use_container_width=True):
                    try:
                        target = build_target_from_form(
                            university_name,
                            country,
                            program_name,
                            normalise_rows(source_rows),
                        )
                        run_and_store_results([target])
                    except ValidationError as exc:
                        st.error(exc)
                    except Exception as exc:
                        st.exception(exc)
            with action_b:
                if st.button("Append to batch editor", use_container_width=True):
                    try:
                        target = build_target_from_form(
                            university_name,
                            country,
                            program_name,
                            normalise_rows(source_rows),
                        )
                        current_targets = parse_targets_json(st.session_state["batch_json"])
                        current_targets.append(target)
                        st.session_state["batch_json"] = serialize_targets(current_targets)
                        st.success("Target appended to batch editor.")
                    except ValidationError as exc:
                        st.error(exc)
                    except Exception as exc:
                        st.exception(exc)

        with batch_tab:
            st.session_state["batch_json"] = st.text_area(
                "Targets JSON",
                value=st.session_state["batch_json"],
                height=420,
            )

            button_a, button_b, button_c = st.columns(3)
            with button_a:
                if st.button("Validate batch", use_container_width=True):
                    try:
                        targets = parse_targets_json(st.session_state["batch_json"])
                        st.success(f"Validated {len(targets)} target(s).")
                    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                        st.error(exc)
            with button_b:
                if st.button("Save input file", use_container_width=True):
                    try:
                        targets = parse_targets_json(st.session_state["batch_json"])
                        DEFAULT_INPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
                        DEFAULT_INPUT_FILE.write_text(
                            serialize_targets(targets),
                            encoding="utf-8",
                        )
                        st.success(f"Saved {len(targets)} target(s) to {DEFAULT_INPUT_FILE}.")
                    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                        st.error(exc)
            with button_c:
                if st.button("Run batch", type="primary", use_container_width=True):
                    try:
                        targets = parse_targets_json(st.session_state["batch_json"])
                        run_and_store_results(targets)
                    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
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

            render_results(results)


if __name__ == "__main__":
    main()
