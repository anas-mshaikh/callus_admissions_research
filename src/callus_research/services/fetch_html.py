from pathlib import Path
import httpx

from callus_research.config import settings


import httpx

from callus_research.config import settings


async def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": settings.user_agent,
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with httpx.AsyncClient(
        timeout=settings.default_timeout,
        headers=headers,
        follow_redirects=True,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def save_raw_html(filename: str, html: str) -> Path:
    raw_dir = settings.data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / filename
    path.write_text(html, encoding="utf-8")
    return path
