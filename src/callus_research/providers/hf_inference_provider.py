import json
from pathlib import Path

from huggingface_hub import InferenceClient
from pydantic import ValidationError

from callus_research.config import settings
from callus_research.logging_utils import get_logger
from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.llm_adjudication import (
    LLMAdjudicationResult,
    WeakFieldSignal,
)
from callus_research.models.llm_extract import LLMExtractionResult
from callus_research.providers.base import BaseExtractionProvider
from callus_research.services.parse_html import html_to_text, read_html

logger = get_logger(__name__)


class HFInferenceExtractionProvider(BaseExtractionProvider):
    def _model_name(self) -> str | None:
        return settings.hf_model_id or settings.llm_model

    def _load_prompt(self, prompt_name: str) -> str:
        return Path(f"src/callus_research/prompts/{prompt_name}").read_text(
            encoding="utf-8"
        )

    def _build_client(self) -> InferenceClient:
        return InferenceClient(
            provider="auto",
            api_key=settings.hf_token,
        )

    def _response_preview(self, response: str, limit: int = 1200) -> str:
        compact = response.strip()
        if len(compact) <= limit:
            return compact
        return compact[:limit] + "... [truncated]"

    def _chat_completion(
        self, client: InferenceClient, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> str:
        model_name = self._model_name()
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
            )
        except Exception:
            logger.exception(
                "HF chat completion failed: model=%s provider=auto max_tokens=%s system_chars=%s user_chars=%s",
                model_name,
                max_tokens,
                len(system_prompt),
                len(user_prompt),
            )
            raise

        response = completion.choices[0].message.content or ""
        logger.info(
            "HF chat completion returned: model=%s chars=%s preview=%r",
            model_name,
            len(response),
            self._response_preview(response),
        )
        return response

    def _parse_response(self, response: str, schema_name: str, parser):
        try:
            payload = json.loads(response)
        except json.JSONDecodeError:
            logger.exception(
                "HF response was not valid JSON: schema=%s preview=%r",
                schema_name,
                self._response_preview(response),
            )
            raise

        try:
            return parser(payload)
        except ValidationError:
            logger.exception(
                "HF JSON failed schema validation: schema=%s payload=%s",
                schema_name,
                json.dumps(payload, ensure_ascii=False)[:2000],
            )
            raise

    def extract(self, request: ExtractFromHtmlRequest) -> LLMExtractionResult:
        html = read_html(request.saved_path)
        text = html_to_text(html)

        client = self._build_client()

        system_prompt = self._load_prompt("extractor.txt").strip()
        user_prompt = f"""
Return valid JSON matching this schema:
{LLMExtractionResult.model_json_schema()}

University: {request.university_name}
Country: {request.country}
Program: {request.program_name}
Source URL: {request.source_url}

PAGE TEXT:
{text[:20000]}
""".strip()

        response = self._chat_completion(
            client,
            system_prompt,
            user_prompt,
            max_tokens=1200,
        )
        return self._parse_response(
            response,
            "LLMExtractionResult",
            LLMExtractionResult.model_validate,
        )

    def adjudicate_field(
        self,
        request: ExtractFromHtmlRequest,
        weak_field: WeakFieldSignal,
    ) -> LLMAdjudicationResult:
        client = self._build_client()
        snippets = (
            "\n".join(f"- {snippet}" for snippet in weak_field.supporting_snippets)
            or "- No supporting snippets available"
        )

        system_prompt = self._load_prompt("adjudicator.txt").strip()
        user_prompt = f"""
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
""".strip()

        response = self._chat_completion(
            client,
            system_prompt,
            user_prompt,
            max_tokens=800,
        )
        return self._parse_response(
            response,
            "LLMAdjudicationResult",
            LLMAdjudicationResult.model_validate,
        )
