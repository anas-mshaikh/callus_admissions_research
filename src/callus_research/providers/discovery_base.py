from abc import ABC, abstractmethod

from callus_research.models.source_bundle import ResearchIntent, SourceType
from callus_research.models.source_discovery import DiscoveredSourceCandidate


class BaseDiscoveryProvider(ABC):
    @abstractmethod
    async def discover_candidates(
        self,
        intent: ResearchIntent,
        source_type: SourceType,
        query: str,
    ) -> list[DiscoveredSourceCandidate]:
        raise NotImplementedError
