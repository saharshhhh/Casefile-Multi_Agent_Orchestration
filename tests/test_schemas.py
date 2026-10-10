import pytest
from pydantic import ValidationError
from schemas.claim import ExtractedClaim
from schemas.review import ReviewVerdict
from schemas.investigation import InvestigationReport

def test_contradicting_report_is_rejected():
    with pytest.raises(ValidationError):
        InvestigationReport(
            prior_claim_ids=[],
            policy_limit=5000,
            within_limit=True,                      # says "within limit"...
            benchmark_repair_cost=900,
            anomaly_flags=["LIMIT_EXCEEDED"],       # ...but also "limit exceeded"
        )
def test_good_claim_passes():
    ExtractedClaim(
        claim_id="C-001", policy_no="P-77", loss_date="2026-09-01",
        line_items=[{"description": "bumper", "amount": 800}],
        estimate_total=800, extraction_confidence=0.93,
    )

def test_free_text_amount_is_rejected():
    with pytest.raises(ValidationError):
        ExtractedClaim(
            claim_id="C-002", policy_no="P-77", loss_date="2026-09-01",
            line_items=[{"description": "bumper", "amount": "around 800 maybe"}],
            estimate_total=800, extraction_confidence=0.9,
        )

def test_invented_verdict_is_rejected():
    with pytest.raises(ValidationError):
        ReviewVerdict(verdict="LOOKS_FINE_I_GUESS")

def test_sendback_needs_a_reason():
    with pytest.raises(ValidationError):
        ReviewVerdict(verdict="SEND_BACK")