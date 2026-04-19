import json
from pathlib import Path

from huggingface_hub import InferenceClient

from callus_research.config import settings
from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.llm_adjudication import (
    LLMAdjudicationResult,
    WeakFieldSignal,
)
from callus_research.models.llm_extract import LLMExtractionResult
from callus_research.providers.base import BaseExtractionProvider
from callus_research.services.parse_html import html_to_text, read_html


class HFInferenceExtractionProvider(BaseExtractionProvider):
    def _model_name(self) -> str | None:
        return settings.hf_model_id or settings.llm_model

    def _load_prompt(self, prompt_name: str) -> str:
        return Path(f"src/callus_research/prompts/{prompt_name}").read_text(encoding="utf-8")

    def _build_client(self) -> InferenceClient:
        return InferenceClient(
            provider="auto",
            api_key=settings.hf_token,
        )

    def extract(self, request: ExtractFromHtmlRequest) -> LLMExtractionResult:
        html = read_html(request.saved_path)
        text = html_to_text(html)

        client = self._build_client()

        prompt = f"""
{self._load_prompt("extractor.txt")}

Return valid JSON matching this schema:
{LLMExtractionResult.model_json_schema()}

University: {request.university_name}
Country: {request.country}
Program: {request.program_name}
Source URL: {request.source_url}

PAGE TEXT:
{text[:20000]}
"""

        # Adjust this call shape based on the model family you choose.
        response = client.text_generation(
            prompt=prompt,
            model=self._model_name(),
            max_new_tokens=1200,
        )

        return LLMExtractionResult.model_validate(json.loads(response))

    def adjudicate_field(
        self,
        request: ExtractFromHtmlRequest,
        weak_field: WeakFieldSignal,
    ) -> LLMAdjudicationResult:
        client = self._build_client()
        snippets = "\n".join(
            f"- {snippet}" for snippet in weak_field.supporting_snippets
        ) or "- No supporting snippets available"

        prompt = f"""
{self._load_prompt("adjudicator.txt")}

Return valid JSON matching this schema:
{LLMAdjudicationResult.model_json_schema()}

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

        response = client.text_generation(
            prompt=prompt,
            model=self._model_name(),
            max_new_tokens=800,
        )

        return LLMAdjudicationResult.model_validate(json.loads(response))
