import config
from graph.runner import run
from schemas.state import ClaimState
from schemas.claim import ExtractedClaim
from schemas.investigation import InvestigationReport
from schemas.review import ReviewVerdict
from schemas.enums import RunStatus


# Fake agents: no AI, they just fill in valid data
def fake_extractor(s):
    s.extracted = ExtractedClaim(
        claim_id="C-1", policy_no="P-1", loss_date="2026-09-01",
        line_items=[{"description": "bumper", "amount": 800}],
        estimate_total=800, extraction_confidence=0.9,
    )

def fake_investigator(s):
    s.investigation = InvestigationReport(
        prior_claim_ids=[], policy_limit=5000, within_limit=True,
        benchmark_repair_cost=900, anomaly_flags=[],
    )

def always_reject_reviewer(s):
    s.review = ReviewVerdict(verdict="SEND_BACK", send_back_reason="ESTIMATE_UNSUPPORTED")

def always_approve_reviewer(s):
    s.review = ReviewVerdict(verdict="APPROVE_RECOMMEND", recommendation_summary="ok")

def expensive_investigator(s):
    fake_investigator(s)
    s.dollars_spent += 1.00     # pretend this call was costly


def test_happy_path_pauses_for_human():
    agents = {"extractor": fake_extractor, "investigator": fake_investigator,
              "reviewer": always_approve_reviewer}
    final = run(ClaimState(claim_id="C-1"), agents)
    assert final.status == RunStatus.AWAITING_APPROVAL
    assert final.path == ["extractor", "investigator", "reviewer"]


def test_endless_rejection_still_terminates():
    agents = {"extractor": fake_extractor, "investigator": fake_investigator,
              "reviewer": always_reject_reviewer}
    final = run(ClaimState(claim_id="C-1"), agents)
    assert final.status == RunStatus.ESCALATED
    assert final.stop_reason == "send-back cap reached"
    assert final.sendback_count == 2


def test_step_cap_stops_the_run(monkeypatch):
    monkeypatch.setattr(config, "MAX_STEPS", 2)
    agents = {"extractor": fake_extractor, "investigator": fake_investigator,
              "reviewer": always_reject_reviewer}
    final = run(ClaimState(claim_id="C-1"), agents)
    assert final.stop_reason == "step cap reached"


def test_budget_cap_stops_the_run():
    agents = {"extractor": fake_extractor, "investigator": expensive_investigator,
              "reviewer": always_reject_reviewer}
    final = run(ClaimState(claim_id="C-1"), agents)
    assert final.stop_reason == "budget cap reached"