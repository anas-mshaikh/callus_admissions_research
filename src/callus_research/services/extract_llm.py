from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.llm_extract import LLMExtractionResult
from callus_research.providers.factory import get_extraction_provider


def extract_with_llm(request: ExtractFromHtmlRequest) -> LLMExtractionResult:
    provider = get_extraction_provider()
    return provider.extract(request)
