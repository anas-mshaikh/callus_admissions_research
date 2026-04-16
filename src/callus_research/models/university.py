from pydantic import BaseModel, HttpUrl


class UniversityTarget(BaseModel):
    university_name: str
    country: str
    program_name: str
    source_url: HttpUrl
