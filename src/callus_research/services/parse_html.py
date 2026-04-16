from pathlib import Path
from bs4 import BeautifulSoup


def read_html(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    return "\n".join(lines)
