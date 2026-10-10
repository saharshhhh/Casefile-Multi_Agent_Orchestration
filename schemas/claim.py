from datetime import date
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    description: str
    amount: float = Field(gt=0)          # must be greater than zero

class ExtractedClaim(BaseModel):
    claim_id: str
    policy_no: str
    loss_date: date
    line_items: list[LineItem] = Field(min_length=1)
    estimate_total: float = Field(gt=0)
    extraction_confidence: float = Field(ge=0, le=1)   # between 0 and 1