from __future__ import annotations

import re

from callus_research.config import settings
from callus_research.logging_utils import get_logger
from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.extraction import FieldEvidence
from callus_research.models.llm_adjudication import (
    FieldEscalationResult,
    FieldName,
    LLMAdjudicationResult,
    WeakFieldSignal,
)
from callus_research.models.verification import VerificationRecord
from callus_research.providers.factory import get_extraction_provider
from callus_research.services.extract_rules import NOTABLE_REQUIREMENT_KEYWORDS
from callus_research.services.parse_html import html_to_text, read_html
from callus_research.services.verify_rules import (
    DATE_PATTERNS,
    ENGLISH_PATTERNS,
    FEE_PATTERNS,
    GENERIC_BAD_VALUES,
    split_lines,
)


FIELD_ORDER: list[FieldName] = [
    "application_deadline",
    "english_proficiency",
    "application_fee",
    "notable_requirement",
]
logger = get_logger(__name__)


def format_adjudication_error(exc: Exception) -> str:
    provider = settings.llm_provider or "unknown"
    model = settings.llm_model or settings.hf_model_id or "unspecified"
    if isinstance(exc, StopIteration):
        detail = "provider returned an empty or malformed structured response"
    else:
        detail = f"{type(exc).__name__}: {exc}"
    return (
        f"LLM adjudication failed for provider={provider}, model={model}. "
        f"{detail}. Verified field was kept."
    )


FIELD_HINTS: dict[FieldName, dict[str, list[str]]] = {
    "application_deadline": {
        "keywords": [
            "deadline",
            "application deadline",
            "apply by",
            "submission deadline",
        ],
        "patterns": DATE_PATTERNS,
    },
    "english_proficiency": {
        "keywords": [
            "toefl",
            "ielts",
            "duolingo",
            "english language",
            "english proficiency",
            "cambridge english",
        ],
        "patterns": ENGLISH_PATTERNS,
    },
    "application_fee": {
        "keywords": ["application fee", "fee", "non-refundable fee"],
        "patterns": FEE_PATTERNS,
    },
    "notable_requirement": {
        "keywords": NOTABLE_REQUIREMENT_KEYWORDS,
        "patterns": [],
    },
}


def value_matches_patterns(value: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, value, re.IGNORECASE) for pattern in patterns)


def describe_weakness(field: FieldEvidence) -> str | None:
    reasons: list[str] = []
    value = (field.value or "").strip()
    normalized = value.lower()

    if field.status == "uncertain":
        reasons.append("rule-based verification could not confirm a supported value")
    if not value:
        reasons.append("no usable value is present")
    elif normalized in GENERIC_BAD_VALUES:
        reasons.append(
            "the current value is a generic label instead of a concrete answer"
        )
    if value and not field.evidence_text:
        reasons.append("the current value has no supporting evidence snippet")

    if (
        field.field_name == "application_deadline"
        and value
        and not value_matches_patterns(value, DATE_PATTERNS)
    ):
        reasons.append("the deadline value does not contain a specific date pattern")
    if (
        field.field_name == "application_fee"
        and value
        and not value_matches_patterns(value, FEE_PATTERNS)
    ):
        reasons.append("the fee value does not contain a concrete currency amount")
    if (
        field.field_name == "english_proficiency"
        and value
        and not value_matches_patterns(value, ENGLISH_PATTERNS)
    ):
        reasons.append(
            "the english requirement does not mention a recognizable test or requirement phrase"
        )
    if field.field_name == "notable_requirement" and value and len(value) < 10:
        reasons.append("the requirement value is too short to be confidently useful")

    if not reasons:
        return None
    return "; ".join(dict.fromkeys(reasons))


def collect_supporting_snippets(field: FieldEvidence, lines: list[str]) -> list[str]:
    config = FIELD_HINTS[field.field_name]  # type: ignore[index]
    snippets: list[str] = []
    value = (field.value or "").strip().lower()
    evidence = (field.evidence_text or "").strip()

    def add_snippet(snippet: str | None) -> None:
        if not snippet:
            return
        cleaned = snippet.strip()
        if not cleaned:
            return
        if cleaned not in snippets:
            snippets.append(cleaned[:400])

    add_snippet(evidence)

    for line in lines:
        lowered = line.lower()
        if value and value in lowered:
            add_snippet(line)
        elif any(keyword in lowered for keyword in config["keywords"]):
            add_snippet(line)
        elif value_matches_patterns(line, config["patterns"]):
            add_snippet(line)
        if len(snippets) >= 6:
            break

    return snippets[:6]


def build_weak_field_signal(
    field: FieldEvidence, source_url: str, lines: list[str]
) -> WeakFieldSignal | None:
    weakness_reason = describe_weakness(field)
    if not weakness_reason:
        return None

    return WeakFieldSignal(
        field_name=field.field_name,  # type: ignore[arg-type]
        current_value=field.value,
        current_status=field.status,
        weakness_reason=weakness_reason,
        source_url=source_url,
        supporting_snippets=collect_supporting_snippets(field, lines),
    )


def merge_adjudicated_field(
    original: FieldEvidence,
    adjudication: LLMAdjudicationResult | None,
    source_url: str,
) -> tuple[FieldEvidence, bool]:
    if not adjudication or adjudication.recommended_action == "unresolved":
        return original, False

    if adjudication.recommended_action == "replace":
        if not adjudication.value:
            return original, False
        value = adjudication.value
    else:
        value = adjudication.value or original.value
        if not value:
            return original, False

    if adjudication.citation_type == "none":
        return original, False

    evidence_text = (
        adjudication.citation or adjudication.evidence_text or original.evidence_text
    )

    return (
        FieldEvidence(
            field_name=original.field_name,
            value=value,
            status="adjudicated",
            evidence_text=evidence_text,
            source_url=source_url,
        ),
        True,
    )


def adjudicate_weak_fields(
    request: ExtractFromHtmlRequest,
    record: VerificationRecord,
) -> tuple[VerificationRecord, list[FieldEscalationResult]]:
    html = read_html(request.saved_path)
    text = html_to_text(html)
    lines = split_lines(text)

    weak_signals: list[WeakFieldSignal] = []
    for field_name in FIELD_ORDER:
        signal = build_weak_field_signal(
            getattr(record, field_name),
            request.source_url,
            lines,
        )
        if signal:
            weak_signals.append(signal)

    if not weak_signals:
        return record, []

    provider = get_extraction_provider()
    logger.info(
        "Escalating %s weak field(s): university=%s program=%s source_url=%s provider=%s",
        len(weak_signals),
        request.university_name,
        request.program_name,
        request.source_url,
        provider.__class__.__name__,
    )
    merged_record = record.model_copy(deep=True)
    escalations: list[FieldEscalationResult] = []

    for signal in weak_signals:
        original_field = getattr(merged_record, signal.field_name)
        try:
            adjudication = provider.adjudicate_field(request, signal)
        except Exception as exc:
            logger.warning(
                "Adjudication failed: university=%s program=%s field=%s url=%s error=%s",
                request.university_name,
                request.program_name,
                signal.field_name,
                signal.source_url,
                format_adjudication_error(exc),
            )
            adjudication = LLMAdjudicationResult(
                field_name=signal.field_name,
                recommended_action="unresolved",
                value=original_field.value,
                confidence=0.0,
                rationale=format_adjudication_error(exc),
                citation_type="none",
                citation=None,
                evidence_text=original_field.evidence_text,
            )
        else:
            logger.info(
                "Adjudication completed: field=%s action=%s confidence=%.2f",
                signal.field_name,
                adjudication.recommended_action,
                adjudication.confidence,
            )
        merged_field, resolved = merge_adjudicated_field(
            original_field,
            adjudication,
            signal.source_url,
        )
        setattr(merged_record, signal.field_name, merged_field)
        escalations.append(
            FieldEscalationResult(
                field_name=signal.field_name,
                current_value=signal.current_value,
                current_status=signal.current_status,
                weakness_reason=signal.weakness_reason,
                supporting_snippets=signal.supporting_snippets,
                adjudication=adjudication,
                resolved=resolved,
                final_value=merged_field.value,
                final_status=merged_field.status,
            )
        )

    return merged_record, escalations
