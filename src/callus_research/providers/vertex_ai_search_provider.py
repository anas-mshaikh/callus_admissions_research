from __future__ import annotations

from pathlib import Path

from google.api_core.client_options import ClientOptions
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.oauth2 import service_account

from callus_research.config import settings
from callus_research.models.source_bundle import ResearchIntent, SourceType
from callus_research.models.source_discovery import DiscoveredSourceCandidate
from callus_research.providers.discovery_base import BaseDiscoveryProvider


def _api_endpoint(location: str) -> str | None:
    return None if location == "global" else f"{location}-discoveryengine.googleapis.com"


def _pick_value(payload: object, keys: tuple[str, ...]) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


class VertexAiSearchDiscoveryProvider(BaseDiscoveryProvider):
    def _build_client(self) -> discoveryengine.SearchServiceClient:
        project_id = settings.vertex_search_project_id
        location = settings.vertex_search_location
        credentials_path = settings.vertex_search_credentials_path

        if not project_id:
            raise ValueError(
                "Vertex AI Search discovery requires VERTEX_SEARCH_PROJECT_ID."
            )

        client_options = None
        endpoint = _api_endpoint(location)
        if endpoint:
            client_options = ClientOptions(api_endpoint=endpoint)

        if credentials_path:
            path = Path(credentials_path)
            if not path.exists():
                raise ValueError(
                    f"Vertex AI Search credentials file does not exist: {path}"
                )
            credentials = service_account.Credentials.from_service_account_file(str(path))
            return discoveryengine.SearchServiceClient(
                credentials=credentials,
                client_options=client_options,
            )

        try:
            return discoveryengine.SearchServiceClient(client_options=client_options)
        except DefaultCredentialsError as exc:
            raise ValueError(
                "Vertex AI Search discovery requires Google ADC credentials or a "
                "service-account JSON path in VERTEX_SEARCH_CREDENTIALS_PATH."
            ) from exc

    def _serving_config(self, client: discoveryengine.SearchServiceClient) -> str:
        project_id = settings.vertex_search_project_id
        location = settings.vertex_search_location
        data_store_id = settings.vertex_search_data_store_id
        serving_config_id = settings.vertex_search_serving_config_id or "default_config"

        if not data_store_id:
            raise ValueError(
                "Vertex AI Search discovery requires VERTEX_SEARCH_DATA_STORE_ID."
            )

        return client.serving_config_path(
            project=project_id,
            location=location,
            data_store=data_store_id,
            serving_config=serving_config_id,
        )

    async def discover_candidates(
        self,
        intent: ResearchIntent,
        source_type: SourceType,
        query: str,
    ) -> list[DiscoveredSourceCandidate]:
        client = self._build_client()
        serving_config = self._serving_config(client)

        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=5,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True
                )
            ),
            query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO
            ),
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
        )

        response = client.search(request=request)
        candidates: list[DiscoveredSourceCandidate] = []
        for result in response:
            document = getattr(result, "document", None)
            derived_struct_data = getattr(document, "derived_struct_data", None)
            struct_data = dict(derived_struct_data) if derived_struct_data else {}
            snippets = getattr(result, "snippet", None)

            url = _pick_value(struct_data, ("link", "url", "uri"))
            title = _pick_value(struct_data, ("title", "pageTitle", "name"))
            snippet_text = None
            if snippets and getattr(snippets, "snippets", None):
                snippet_items = getattr(snippets, "snippets")
                if snippet_items:
                    snippet_text = getattr(snippet_items[0], "snippet", None)

            if not url:
                continue

            candidates.append(
                DiscoveredSourceCandidate(
                    source_type=source_type,
                    query=query,
                    url=url,
                    title=title,
                    reason=snippet_text or "Returned by Vertex AI Search.",
                    confidence=0.5,
                )
            )

        return candidates
