import httpx

from callus_research.config import settings
from callus_research.models.source_bundle import ResearchIntent
from callus_research.models.source_common import SourceType
from callus_research.models.source_discovery import DiscoveredSourceCandidate
from callus_research.providers.discovery_base import BaseDiscoveryProvider


class GoogleCustomSearchDiscoveryProvider(BaseDiscoveryProvider):
    async def discover_candidates(
        self,
        intent: ResearchIntent,
        source_type: SourceType,
        query: str,
    ) -> list[DiscoveredSourceCandidate]:
        api_key = settings.google_search_api_key or settings.google_api_key
        engine_id = settings.google_search_engine_id

        if not api_key:
            raise ValueError(
                "Google Custom Search discovery requires GOOGLE_SEARCH_API_KEY "
                "or GOOGLE_API_KEY."
            )
        if not engine_id:
            raise ValueError(
                "Google Custom Search discovery requires GOOGLE_SEARCH_ENGINE_ID."
            )

        async with httpx.AsyncClient(timeout=settings.default_timeout) as client:
            response = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": api_key,
                    "cx": engine_id,
                    "q": query,
                    "num": 5,
                },
            )
            response.raise_for_status()
            payload = response.json()

        items = payload.get("items", [])
        return [
            DiscoveredSourceCandidate(
                source_type=source_type,
                query=query,
                url=item["link"],
                title=item.get("title"),
                reason=item.get("snippet") or "Returned by Google Custom Search.",
                confidence=0.45,
            )
            for item in items
            if item.get("link")
        ]
