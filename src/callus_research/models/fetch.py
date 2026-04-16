from typing import Literal
from pydantic import BaseModel, HttpUrl


class FetchRequest(BaseModel):
    university_name: str
    country: str
    program_name: str
    source_url: HttpUrl
    mode: Literal["auto", "http", "browser"] = "auto"


class FetchResult(BaseModel):
    university_name: str
    program_name: str
    source_url: str
    fetch_mode: Literal["http", "browser"]
    saved_path: str
    content_length: int
    title: str | None = None
