from pydantic import BaseModel, model_validator
from .enums import AnomalyFlag


class InvestigationReport(BaseModel):
    prior_claim_ids: list[str]
    policy_limit: float
    within_limit: bool
    benchmark_repair_cost: float
    anomaly_flags: list[AnomalyFlag]
    notes: list[str] = []

    @model_validator(mode="after")
    def check_limit_flag(self):
        if self.within_limit and AnomalyFlag.LIMIT_EXCEEDED in self.anomaly_flags:
            raise ValueError("within_limit is True but LIMIT_EXCEEDED is flagged")
        return self