from callus_research.config import settings
from callus_research.providers.adk_google_search_provider import (
    AdkGoogleSearchDiscoveryProvider,
)
from callus_research.providers.discovery_base import BaseDiscoveryProvider


def get_discovery_provider() -> BaseDiscoveryProvider:
    provider = settings.discovery_provider.lower()

    if provider == "adk_google_search":
        return AdkGoogleSearchDiscoveryProvider()

    raise ValueError(f"Unsupported DISCOVERY_PROVIDER: {settings.discovery_provider}")
