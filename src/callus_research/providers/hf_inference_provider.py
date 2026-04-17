import json
from pathlib import Path

from huggingface_hub import InferenceClient

from callus_research.config import settings
from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.llm_extract import LLMExtractionResult
from callus_research.providers.base import BaseExtractionProvider
from callus_research.services.parse_html import html_to_text, read_html


class HFInferenceExtractionProvider(BaseExtractionProvider):
    def _load_prompt(self) -> str:
        return Path("src/callus_research/prompts/extractor.txt").read_text(
            encoding="utf-8"
        )

    def extract(self, request: ExtractFromHtmlRequest) -> LLMExtractionResult:
        html = read_html(request.saved_path)
        text = html_to_text(html)

        client = InferenceClient(
            provider="auto",
            api_key=settings.hf_token,
        )

        prompt = f"""
{self._load_prompt()}

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
            model=settings.hf_model_id,
            max_new_tokens=1200,
        )

        return LLMExtractionResult.model_validate(json.loads(response))
