from __future__ import annotations

from urllib.parse import urlparse

from callus_research.logging_utils import get_logger
from callus_research.models.source_bundle import ResearchIntent, ResearchTarget
from callus_research.models.source_common import SourcePage, SourceType
from callus_research.models.source_discovery import (
    DiscoveredSourceCandidate,
    SourceDiscoveryResult,
)
from callus_research.providers.discovery_factory import get_discovery_provider

logger = get_logger(__name__)


DISCOVERY_QUERIES: dict[SourceType, str] = {
    "program_page": "{university_name} {program_name} {degree_type} official program page",
    "admissions_page": "{university_name} {program_name} {degree_type} official admissions requirements",
    "english_requirements_page": "{university_name} {program_name} {degree_type} official english language requirements",
    "fee_page": "{university_name} {degree_type} official application fee",
    "application_checklist": "{university_name} {program_name} {degree_type} official application checklist",
    "deadline_page": "{university_name} {program_name} {degree_type} official application deadline",
    "other": "{university_name} {program_name} {degree_type} official admissions",
}

PRIORITY_SOURCE_TYPES: list[SourceType] = [
    "program_page",
    "admissions_page",
    "english_requirements_page",
    "fee_page",
]

BLOCKED_HOST_FRAGMENTS = {
    "wikipedia.org",
    "mastersportal.com",
    "topuniversities.com",
    "findaphd.com",
    "findamasters.com",
    "shiksha.com",
    "yocket.com",
    "linkedin.com",
    "idp.com",
    "leverageedu.com",
    "qs.com",
}

PATH_HINTS: dict[SourceType, tuple[str, ...]] = {
    "program_page": ("program", "course", "curriculum", "computer-science", "eecs"),
    "admissions_page": ("admission", "admissions", "apply", "graduate", "postgraduate"),
    "english_requirements_page": (
        "english",
        "language",
        "ielts",
        "toefl",
        "requirements",
    ),
    "fee_page": ("fee", "fees", "tuition", "application-fee"),
}


def normalise_url(url: str) -> str:
    return url.rstrip("/")


def host_is_official(intent: ResearchIntent, host: str) -> bool:
    lowered = host.lower()
    if any(fragment in lowered for fragment in BLOCKED_HOST_FRAGMENTS):
        return False

    university_tokens = [
        token
        for token in intent.university_name.lower().replace("-", " ").split()
        if len(token) > 2 and token not in {"university", "institute", "college", "the"}
    ]

    official_tld = lowered.endswith(
        (".edu", ".ac.uk", ".edu.au", ".ac.jp", ".edu.cn", ".edu.sg", ".edu.hk")
    )
    token_match = any(token in lowered for token in university_tokens)
    return official_tld or token_match


def score_candidate(
    intent: ResearchIntent, candidate: DiscoveredSourceCandidate
) -> tuple[int, bool]:
    parsed = urlparse(candidate.url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    title = (candidate.title or "").lower()
    is_official = host_is_official(intent, host)
    score = 0

    if is_official:
        score += 50

    program_tokens = [
        token
        for token in intent.program_name.lower().replace("-", " ").split()
        if len(token) > 2
    ]
    degree_tokens = [
        token
        for token in intent.degree_type.lower().replace("-", " ").split()
        if len(token) > 1
    ]

    combined = f"{host} {path} {title}"
    score += sum(8 for token in program_tokens if token in combined)
    score += sum(4 for token in degree_tokens if token in combined)

    for hint in PATH_HINTS.get(candidate.source_type, ()):
        if hint in combined:
            score += 6

    score += int(candidate.confidence * 20)
    return score, is_official


def build_research_target(
    intent: ResearchIntent, selected_sources: list[SourcePage]
) -> ResearchTarget:
    return ResearchTarget(
        university_name=intent.university_name,
        country=intent.country,
        program_name=intent.program_name,
        sources=selected_sources,
    )


def dedupe_selected_sources(
    candidates: list[DiscoveredSourceCandidate],
) -> list[SourcePage]:
    seen: set[str] = set()
    selected_sources: list[SourcePage] = []
    for candidate in candidates:
        if not candidate.selected:
            continue
        normalised = normalise_url(candidate.url)
        if normalised in seen:
            continue
        seen.add(normalised)
        selected_sources.append(
            SourcePage(
                url=normalised,
                source_type=candidate.source_type,
                mode="auto",
            )
        )
    return selected_sources


async def discover_sources(intent: ResearchIntent) -> SourceDiscoveryResult:
    provider = get_discovery_provider()
    logger.info(
        "Running discovery with provider=%s for university=%s program=%s",
        provider.__class__.__name__,
        intent.university_name,
        intent.program_name,
    )
    search_queries = [
        DISCOVERY_QUERIES[source_type].format(
            university_name=intent.university_name,
            program_name=intent.program_name,
            degree_type=intent.degree_type,
        )
        for source_type in PRIORITY_SOURCE_TYPES
    ]

    candidates: list[DiscoveredSourceCandidate] = []
    for source_type, query in zip(PRIORITY_SOURCE_TYPES, search_queries):
        logger.info("Discovery query: source_type=%s query=%s", source_type, query)
        try:
            results = await provider.discover_candidates(intent, source_type, query)
        except Exception as exc:
            logger.exception(
                "Discovery provider failed: university=%s program=%s source_type=%s",
                intent.university_name,
                intent.program_name,
                source_type,
            )
            raise ValueError(
                f"Source discovery failed for {source_type} using query '{query}'. {exc}"
            ) from exc
        if not results:
            logger.warning(
                "Discovery returned no candidates: university=%s program=%s source_type=%s",
                intent.university_name,
                intent.program_name,
                source_type,
            )
            continue

        ranked = sorted(
            results,
            key=lambda candidate: score_candidate(intent, candidate)[0],
            reverse=True,
        )
        for index, candidate in enumerate(ranked):
            score, is_official = score_candidate(intent, candidate)
            candidate.is_official = is_official
            candidate.selected = index == 0 and is_official and score >= 60
            if not candidate.selected:
                candidate.rejection_reason = (
                    "lower-ranked candidate"
                    if is_official
                    else "not an official university domain"
                )
            candidates.append(candidate)
        logger.info(
            "Discovery ranked %s candidate(s) for source_type=%s",
            len(ranked),
            source_type,
        )

    selected_sources = dedupe_selected_sources(candidates)
    summary = (
        f"Selected {len(selected_sources)} official source page(s) from "
        f"{len(candidates)} discovered candidate(s)."
    )
    logger.info(
        "Discovery summary: university=%s program=%s selected=%s candidates=%s",
        intent.university_name,
        intent.program_name,
        len(selected_sources),
        len(candidates),
    )

    return SourceDiscoveryResult(
        university_name=intent.university_name,
        country=intent.country,
        program_name=intent.program_name,
        degree_type=intent.degree_type,
        search_queries=search_queries,
        candidates=candidates,
        selected_sources=selected_sources,
        summary=summary,
    )
