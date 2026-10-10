from schemas.enums import RunStatus
from store.approvals import ApprovalError


def decide(claim_id, decision, approver, store, approvals, claims):
    """A person's decision on a paused claim."""
    if decision not in ("approve", "reject"):
        raise ApprovalError("decision must be 'approve' or 'reject'")

    state = store.load_latest(claim_id)
    if state is None:
        raise ApprovalError("no run found for this claim")
    if state.status != RunStatus.AWAITING_APPROVAL:
        raise ApprovalError(f"claim is not waiting for approval (status: {state.status.value})")

    approval_id = approvals.record(claim_id, decision, approver)

    if decision == "approve":
        summary = state.review.recommendation_summary or ""
        claims.write_back(claim_id, summary, approval_id)
        state.status = RunStatus.DONE
    else:
        state.status = RunStatus.REJECTED
        state.stop_reason = "rejected by human"

    state.approval_id = approval_id
    store.save_snapshot(state)
    return state