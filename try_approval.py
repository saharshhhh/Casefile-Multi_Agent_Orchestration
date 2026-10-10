from agents.extractor import make_extractor
from agents.investigator import investigator
from agents.reviewer import make_reviewer
from graph.approval_gate import decide
from graph.runner import run
from llm.client import LLMClient
from schemas.enums import RunStatus
from schemas.state import ClaimState
from store.approvals import ApprovalStore
from store.claims_system import ClaimsSystem
from store.snapshots import SnapshotStore

text = """
Claim number: C-3001
Policy: P-5531
Date of loss: 5 October 2026
Rear bumper replacement: 850.00
Paint and labour: 420.50
Total estimate: 1270.50
"""

store = SnapshotStore()
approvals = ApprovalStore()
claims = ClaimsSystem(approvals)

llm = LLMClient()
agents = {
    "extractor": make_extractor(llm),
    "investigator": investigator,
    "reviewer": make_reviewer(llm),
}

state = run(ClaimState(claim_id="C-3001", claim_text=text), agents, store)
print("path:  ", " -> ".join(state.path))
print("status:", state.status.value)

if state.status != RunStatus.AWAITING_APPROVAL:
    print("Stopped before the gate:", state.stop_reason)
else:
    print("Recommendation:", state.review.recommendation_summary)
    print("Writes so far:", claims.get_writebacks("C-3001"))
    choice = input("Type approve or reject: ").strip().lower()
    final = decide("C-3001", choice, "adjuster_1", store, approvals, claims)
    print("final status:", final.status.value)
    print("approval id: ", final.approval_id)
    print("Writes now:  ", claims.get_writebacks("C-3001"))