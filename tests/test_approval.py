import pytest
from graph.approval_gate import decide
from graph.runner import run
from schemas.enums import RunStatus
from schemas.state import ClaimState
from store.approvals import ApprovalError, ApprovalStore
from store.claims_system import ClaimsSystem
from store.snapshots import SnapshotStore
from tests.test_guards import (
    fake_extractor, fake_investigator,
    always_approve_reviewer, always_reject_reviewer,
)


def setup(tmp_path):
    """A claim that has been reviewed and is waiting for a human."""
    db = str(tmp_path / "test.db")
    store = SnapshotStore(db)
    approvals = ApprovalStore(db)
    claims = ClaimsSystem(approvals, db)

    agents = {
        "extractor": fake_extractor,
        "investigator": fake_investigator,
        "reviewer": always_approve_reviewer,
    }
    run(ClaimState(claim_id="C-1"), agents, store)
    return store, approvals, claims


def test_run_pauses_and_nothing_is_written(tmp_path):
    store, approvals, claims = setup(tmp_path)

    assert store.load_latest("C-1").status == RunStatus.AWAITING_APPROVAL
    assert claims.get_writebacks("C-1") == []


def test_approval_finishes_the_run_and_writes_back(tmp_path):
    store, approvals, claims = setup(tmp_path)

    final = decide("C-1", "approve", "adjuster_1", store, approvals, claims)

    assert final.status == RunStatus.DONE
    assert final.approval_id is not None
    assert len(claims.get_writebacks("C-1")) == 1
    assert store.load_latest("C-1").status == RunStatus.DONE


def test_rejection_writes_nothing(tmp_path):
    store, approvals, claims = setup(tmp_path)

    final = decide("C-1", "reject", "adjuster_1", store, approvals, claims)

    assert final.status == RunStatus.REJECTED
    assert claims.get_writebacks("C-1") == []


def test_write_back_refuses_without_approval(tmp_path):
    store, approvals, claims = setup(tmp_path)

    with pytest.raises(ApprovalError):
        claims.write_back("C-1", "pay it", None)
    with pytest.raises(ApprovalError):
        claims.write_back("C-1", "pay it", "made-up-id")
    assert claims.get_writebacks("C-1") == []


def test_approval_for_another_claim_is_refused(tmp_path):
    store, approvals, claims = setup(tmp_path)
    slip = approvals.record("C-2", "approve", "adjuster_1")

    with pytest.raises(ApprovalError):
        claims.write_back("C-1", "pay it", slip)


def test_a_rejection_cannot_be_used_to_write(tmp_path):
    store, approvals, claims = setup(tmp_path)
    slip = approvals.record("C-1", "reject", "adjuster_1")

    with pytest.raises(ApprovalError):
        claims.write_back("C-1", "pay it", slip)


def test_approval_cannot_be_used_twice(tmp_path):
    store, approvals, claims = setup(tmp_path)
    slip = approvals.record("C-1", "approve", "adjuster_1")

    claims.write_back("C-1", "pay it", slip)
    with pytest.raises(ApprovalError):
        claims.write_back("C-1", "pay it", slip)
    assert len(claims.get_writebacks("C-1")) == 1


def test_cannot_decide_twice(tmp_path):
    store, approvals, claims = setup(tmp_path)
    decide("C-1", "approve", "adjuster_1", store, approvals, claims)

    with pytest.raises(ApprovalError):
        decide("C-1", "approve", "adjuster_1", store, approvals, claims)


def test_cannot_approve_an_escalated_claim(tmp_path):
    db = str(tmp_path / "test.db")
    store, approvals = SnapshotStore(db), ApprovalStore(db)
    claims = ClaimsSystem(approvals, db)
    agents = {
        "extractor": fake_extractor,
        "investigator": fake_investigator,
        "reviewer": always_reject_reviewer,
    }
    run(ClaimState(claim_id="C-9"), agents, store)     # ends as ESCALATED

    with pytest.raises(ApprovalError):
        decide("C-9", "approve", "adjuster_1", store, approvals, claims)