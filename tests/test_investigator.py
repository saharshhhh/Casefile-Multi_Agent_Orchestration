import pytest
from agents.base import AgentError
from agents.investigator import investigator
from graph.runner import run
from schemas.claim import ExtractedClaim
from schemas.enums import AnomalyFlag, RunStatus
from schemas.state import ClaimState
from tools.tools import call_tool


def make_state(policy_no, total, loss_date="2026-09-03", claim_id="C-2000"):
    state = ClaimState(claim_id=claim_id)
    state.extracted = ExtractedClaim(
        claim_id=claim_id, policy_no=policy_no, loss_date=loss_date,
        line_items=[{"description": "repair", "amount": total}],
        estimate_total=total, extraction_confidence=0.9,
    )
    return state


def test_normal_claim_has_no_flags():
    state = make_state("P-5531", 1270.50)
    investigator(state)
    report = state.investigation

    assert report.anomaly_flags == []
    assert report.within_limit is True
    assert report.prior_claim_ids == ["C-0877"]
    assert report.benchmark_repair_cost == 1400


def test_claim_over_the_limit_is_flagged():
    state = make_state("P-7001", 2000, loss_date="2026-09-10")
    investigator(state)

    assert AnomalyFlag.LIMIT_EXCEEDED in state.investigation.anomaly_flags
    assert state.investigation.within_limit is False


def test_same_day_claim_is_flagged_as_duplicate():
    state = make_state("P-7001", 900, loss_date="2026-09-03")
    investigator(state)

    assert AnomalyFlag.DUPLICATE_CLAIM_SUSPECTED in state.investigation.anomaly_flags


def test_inflated_estimate_is_flagged():
    state = make_state("P-5531", 4000)
    investigator(state)

    assert AnomalyFlag.ESTIMATE_ABOVE_BENCHMARK in state.investigation.anomaly_flags


def test_unknown_policy_escalates():
    state = make_state("P-0000", 500)
    final = run(state, {"investigator": investigator})

    assert final.status == RunStatus.ESCALATED
    assert "investigator failed" in final.stop_reason


def test_tool_refuses_wrong_input():
    with pytest.raises(AgentError):
        call_tool("lookup_policy", {"policy": "P-5531"})    # wrong field name


def test_unknown_tool_is_refused():
    with pytest.raises(AgentError):
        call_tool("delete_everything", {})