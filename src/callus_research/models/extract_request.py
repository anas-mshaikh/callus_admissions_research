from pydantic import BaseModel


class ExtractFromHtmlRequest(BaseModel):
    university_name: str
    country: str
    program_name: str
    source_url: str
    saved_path: str
