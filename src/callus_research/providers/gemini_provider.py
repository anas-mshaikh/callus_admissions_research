from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI

from callus_research.config import settings
from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.llm_extract import LLMExtractionResult
from callus_research.providers.base import BaseExtractionProvider
from callus_research.services.parse_html import html_to_text, read_html


class GeminiExtractionProvider(BaseExtractionProvider):
    def _load_prompt(self) -> str:
        return Path("src/callus_research/prompts/extractor.txt").read_text(
            encoding="utf-8"
        )

    def extract(self, request: ExtractFromHtmlRequest) -> LLMExtractionResult:
        html = read_html(request.saved_path)
        text = html_to_text(html)

        llm = ChatGoogleGenerativeAI(
            model=settings.llm_model or "gemini-2.5-pro",
            google_api_key=settings.google_api_key,
            temperature=0,
        )

        structured_llm = llm.with_structured_output(LLMExtractionResult)

        message = f"""
{self._load_prompt()}

University: {request.university_name}
Country: {request.country}
Program: {request.program_name}
Source URL: {request.source_url}

PAGE TEXT:
{text[:30000]}
"""
        return structured_llm.invoke(message)
