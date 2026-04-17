from callus_research.config import settings
from callus_research.providers.base import BaseExtractionProvider


def get_extraction_provider() -> BaseExtractionProvider:
    provider = settings.llm_provider.lower()

    if provider == "openai":
        from callus_research.providers.openai_provider import OpenAIExtractionProvider

        return OpenAIExtractionProvider()
    if provider == "gemini":
        from callus_research.providers.gemini_provider import GeminiExtractionProvider

        return GeminiExtractionProvider()
    if provider == "hf_inference":
        from callus_research.providers.hf_inference_provider import (
            HFInferenceExtractionProvider,
        )

        return HFInferenceExtractionProvider()

    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
