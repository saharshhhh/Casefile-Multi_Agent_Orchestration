from pydantic import BaseModel


class LookupPolicyInput(BaseModel):
    policy_no: str


class PriorClaimsInput(BaseModel):
    policy_no: str


class BenchmarkInput(BaseModel):
    vehicle: str