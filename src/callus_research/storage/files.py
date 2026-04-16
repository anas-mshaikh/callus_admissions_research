from pathlib import Path
from slugify import slugify

from callus_research.config import settings


def ensure_data_dirs() -> None:
    for name in ["raw", "parsed", "verified", "outputs"]:
        (settings.data_dir / name).mkdir(parents=True, exist_ok=True)


def build_raw_html_path(
    university_name: str, program_name: str, fetch_mode: str
) -> Path:
    ensure_data_dirs()
    uni = slugify(university_name)
    program = slugify(program_name)
    filename = f"{uni}__{program}__{fetch_mode}.html"
    return settings.data_dir / "raw" / filename


def save_raw_html(
    university_name: str, program_name: str, fetch_mode: str, html: str
) -> Path:
    path = build_raw_html_path(university_name, program_name, fetch_mode)
    path.write_text(html, encoding="utf-8")
    return path
