from observability.tracing import setup_tracing
setup_tracing()
from agents.extractor import make_extractor
from agents.investigator import investigator
from agents.reviewer import make_reviewer
from graph.runner import run
from llm.client import LLMClient
from schemas.state import ClaimState
from store.snapshots import SnapshotStore

text = """
Claim number: C-2001
Policy: P-5531
Date of loss: 20 September 2026
Front bumper and grille replacement: 1900.00
Hood repair and paint: 1500.00
Labour: 800.00
Total estimate: 4200.00
"""

llm = LLMClient()
agents = {
    "extractor": make_extractor(llm),
    "investigator": investigator,
    "reviewer": make_reviewer(llm),
}

state = ClaimState(claim_id="C-2001", claim_text=text)
final = run(state, agents, SnapshotStore())

print("path:   ", " -> ".join(final.path))
print("status: ", final.status.value)
print("reason: ", final.stop_reason)
print("notes:  ", final.investigation.notes if final.investigation else None)
print("tokens: ", final.tokens_used, " dollars:", round(final.dollars_spent, 5))