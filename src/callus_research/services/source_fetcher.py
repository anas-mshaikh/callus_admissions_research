from bs4 import BeautifulSoup

from callus_research.models.fetch import FetchRequest, FetchResult
from callus_research.services.fetch_browser import fetch_rendered_html
from callus_research.services.fetch_html import fetch_html
from callus_research.storage.files import save_raw_html


def extract_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    return title


def looks_like_blocked_or_empty(html: str) -> bool:
    lowered = html.lower()
    too_short = len(html.strip()) < 2000
    blocked_signals = [
        "enable javascript",
        "access denied",
        "captcha",
        "temporarily unavailable",
    ]
    return too_short or any(signal in lowered for signal in blocked_signals)


async def fetch_source(request: FetchRequest) -> FetchResult:
    html = ""
    mode_used = request.mode

    if request.mode in ("auto", "http"):
        try:
            html = await fetch_html(str(request.source_url))
            if request.mode == "auto" and looks_like_blocked_or_empty(html):
                html = await fetch_rendered_html(str(request.source_url))
                mode_used = "browser"
            else:
                mode_used = "http"
        except Exception:
            if request.mode == "http":
                raise
            html = await fetch_rendered_html(str(request.source_url))
            mode_used = "browser"

    elif request.mode == "browser":
        html = await fetch_rendered_html(str(request.source_url))
        mode_used = "browser"

    saved_path = save_raw_html(
        university_name=request.university_name,
        program_name=request.program_name,
        fetch_mode=mode_used,
        html=html,
    )

    return FetchResult(
        university_name=request.university_name,
        program_name=request.program_name,
        source_url=str(request.source_url),
        fetch_mode=mode_used,
        saved_path=str(saved_path),
        content_length=len(html),
        title=extract_title(html),
    )
