from pydantic import BaseModel

from callus_research.models.extract_request import ExtractFromHtmlRequest
from callus_research.models.verification import VerificationRecord


class LLMRetryRequest(BaseModel):
    html_request: ExtractFromHtmlRequest
    verified_record: VerificationRecord
