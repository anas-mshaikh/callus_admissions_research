from abc import ABC, abstractmethod

from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.llm_adjudication import (
    LLMAdjudicationResult,
    WeakFieldSignal,
)
from callus_research.models.llm_extract import LLMExtractionResult


class BaseExtractionProvider(ABC):
    @abstractmethod
    def extract(self, request: ExtractFromHtmlRequest) -> LLMExtractionResult:
        raise NotImplementedError

    @abstractmethod
    def adjudicate_field(
        self,
        request: ExtractFromHtmlRequest,
        weak_field: WeakFieldSignal,
    ) -> LLMAdjudicationResult:
        raise NotImplementedError
