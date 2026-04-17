from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI

from callus_research.config import settings
from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.llm_adjudication import (
    LLMAdjudicationResult,
    WeakFieldSignal,
)
from callus_research.models.llm_extract import LLMExtractionResult
from callus_research.providers.base import BaseExtractionProvider
from callus_research.services.parse_html import html_to_text, read_html


class GeminiExtractionProvider(BaseExtractionProvider):
    def _load_prompt(self, prompt_name: str) -> str:
        return Path(f"src/callus_research/prompts/{prompt_name}").read_text(encoding="utf-8")

    def _build_llm(self) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=settings.llm_model or "gemini-2.5-pro",
            google_api_key=settings.google_api_key,
            temperature=0,
        )

    def extract(self, request: ExtractFromHtmlRequest) -> LLMExtractionResult:
        html = read_html(request.saved_path)
        text = html_to_text(html)

        llm = self._build_llm()
        structured_llm = llm.with_structured_output(LLMExtractionResult)

        message = f"""
{self._load_prompt("extractor.txt")}

University: {request.university_name}
Country: {request.country}
Program: {request.program_name}
Source URL: {request.source_url}

PAGE TEXT:
{text[:30000]}
"""
        return structured_llm.invoke(message)

    def adjudicate_field(
        self,
        request: ExtractFromHtmlRequest,
        weak_field: WeakFieldSignal,
    ) -> LLMAdjudicationResult:
        llm = self._build_llm()
        structured_llm = llm.with_structured_output(LLMAdjudicationResult)

        snippets = "\n".join(
            f"- {snippet}" for snippet in weak_field.supporting_snippets
        ) or "- No supporting snippets available"

        message = f"""
{self._load_prompt("adjudicator.txt")}

University: {request.university_name}
Country: {request.country}
Program: {request.program_name}
Source URL: {weak_field.source_url}
Field: {weak_field.field_name}
Current status: {weak_field.current_status}
Current value: {weak_field.current_value}
Weakness reason: {weak_field.weakness_reason}

Supporting snippets:
{snippets}
"""
        return structured_llm.invoke(message)
