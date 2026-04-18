from __future__ import annotations

import json
import os
import re
from uuid import uuid4

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types

from callus_research.config import settings
from callus_research.models.source_bundle import ResearchIntent, SourceType
from callus_research.models.source_discovery import DiscoveredSourceCandidate
from callus_research.providers.discovery_base import BaseDiscoveryProvider


def extract_json_object(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Discovery response did not contain a JSON object.")

    return json.loads(cleaned[start : end + 1])


class AdkGoogleSearchDiscoveryProvider(BaseDiscoveryProvider):
    async def discover_candidates(
        self,
        intent: ResearchIntent,
        source_type: SourceType,
        query: str,
    ) -> list[DiscoveredSourceCandidate]:
        if not settings.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY is required for ADK Google Search discovery."
            )

        os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)

        instruction = (
            "You are a source discovery agent for university admissions research. "
            "Use Google Search to find likely official university URLs for the requested "
            "program and return only JSON with a top-level 'candidates' array."
        )

        agent = Agent(
            name="official_source_discovery_agent",
            model=settings.discovery_model,
            description="Discovers official university admissions URLs with Google Search.",
            instruction=instruction,
            tools=[google_search],
        )

        session_service = InMemorySessionService()
        app_name = "callus_source_discovery"
        user_id = "callus_operator"
        session_id = f"{source_type}-{uuid4().hex}"
        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )
        runner = Runner(
            agent=agent,
            app_name=app_name,
            session_service=session_service,
        )

        prompt = f"""
{settings.source_discovery_prompt}

University: {intent.university_name}
Country: {intent.country}
Program: {intent.program_name}
Degree type: {intent.degree_type}
Requested source type: {source_type}
Search query: {query}

Return a JSON object with this shape:
{{
  "candidates": [
    {{
      "url": "https://...",
      "title": "Page title",
      "reason": "Why this page is relevant",
      "confidence": 0.0
    }}
  ]
}}
"""

        content = types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        )

        final_response = ""
        events = runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        )
        async for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                final_response = "".join(
                    part.text or "" for part in event.content.parts
                )

        payload = extract_json_object(final_response)
        candidates = payload.get("candidates", [])

        return [
            DiscoveredSourceCandidate(
                source_type=source_type,
                query=query,
                url=item["url"],
                title=item.get("title"),
                reason=item.get("reason", ""),
                confidence=float(item.get("confidence", 0.0)),
            )
            for item in candidates
            if item.get("url")
        ]
