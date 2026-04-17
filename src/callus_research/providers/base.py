from abc import ABC, abstractmethod

from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.llm_extract import LLMExtractionResult


class BaseExtractionProvider(ABC):
    @abstractmethod
    def extract(self, request: ExtractFromHtmlRequest) -> LLMExtractionResult:
        raise NotImplementedError
