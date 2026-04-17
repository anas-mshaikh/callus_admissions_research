from callus_research.config import settings
from callus_research.providers.base import BaseExtractionProvider
from callus_research.providers.gemini_provider import GeminiExtractionProvider
from callus_research.providers.hf_inference_provider import (
    HFInferenceExtractionProvider,
)
# from callus_research.providers.openai_provider import OpenAIExtractionProvider


def get_extraction_provider() -> BaseExtractionProvider:
    provider = settings.llm_provider.lower()

    # if provider == "openai":
    #     return OpenAIExtractionProvider()
    if provider == "gemini":
        return GeminiExtractionProvider()
    if provider == "hf_inference":
        return HFInferenceExtractionProvider()

    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
