from pydantic import BaseModel
from .enums import RunStatus, SendBackReason
from .claim import ExtractedClaim
from .investigation import InvestigationReport
from .review import ReviewVerdict

class ClaimState(BaseModel):
    claim_id: str
    claim_text: str = ""
    status: RunStatus = RunStatus.RUNNING
    stop_reason: str | None = None
    sendback_reason: SendBackReason | None = None
    # each agent owns exactly one slice
    extracted: ExtractedClaim | None = None
    investigation: InvestigationReport | None = None
    review: ReviewVerdict | None = None
    approval_id: str | None = None
    # control fields: only the supervisor writes these
    step_count: int = 0
    sendback_count: int = 0
    tokens_used: int = 0
    llm_calls: int = 0
    dollars_spent: float = 0.0
    path: list[str] = []