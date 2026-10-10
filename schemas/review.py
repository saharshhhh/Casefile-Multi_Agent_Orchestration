from pydantic import BaseModel, model_validator
from .enums import Verdict, SendBackReason

class ReviewVerdict(BaseModel):
    verdict: Verdict
    send_back_reason: SendBackReason | None = None
    recommendation_summary: str | None = None

    @model_validator(mode="after")
    def check_consistency(self):
        if self.verdict == Verdict.SEND_BACK and self.send_back_reason is None:
            raise ValueError("SEND_BACK requires a send_back_reason")
        return self