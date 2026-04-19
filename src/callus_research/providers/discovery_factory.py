from callus_research.config import settings
from callus_research.providers.adk_google_search_provider import (
    AdkGoogleSearchDiscoveryProvider,
)
from callus_research.providers.discovery_base import BaseDiscoveryProvider
from callus_research.providers.google_custom_search_provider import (
    GoogleCustomSearchDiscoveryProvider,
)
from callus_research.providers.vertex_ai_search_provider import (
    VertexAiSearchDiscoveryProvider,
)


def get_discovery_provider() -> BaseDiscoveryProvider:
    provider = settings.discovery_provider.lower()

    if provider == "adk_google_search":
        return AdkGoogleSearchDiscoveryProvider()
    if provider == "google_custom_search":
        return GoogleCustomSearchDiscoveryProvider()
    if provider == "vertex_ai_search":
        return VertexAiSearchDiscoveryProvider()

    raise ValueError(f"Unsupported DISCOVERY_PROVIDER: {settings.discovery_provider}")
