import json
import os
import sqlite3

import config
from agents.extractor import make_extractor
from agents.investigator import investigator
from agents.reviewer import make_reviewer
from graph.runner import run
from llm.client import LLMClient
from llm.recording import RecordingLLM
from observability.tracing import setup_tracing
from schemas.state import ClaimState
from store.snapshots import SnapshotStore

RESULTS = "results.json"
DB = "casefile.db"

setup_tracing("traces.jsonl")

with open("data/claims.json", encoding="utf-8") as f:
    claims = json.load(f)

# Claims finished in an earlier run are skipped, so you can stop and restart safely
done = {}
if os.path.exists(RESULTS):
    with open(RESULTS, encoding="utf-8") as f:
        done = {r["claim_id"]: r for r in json.load(f)}


def forget(claim_id):
    """Wipe leftovers from an earlier failed attempt at this claim."""
    db = sqlite3.connect(DB)
    db.execute("DELETE FROM snapshots WHERE claim_id = ?", (claim_id,))
    db.execute("DELETE FROM llm_calls WHERE claim_id = ?", (claim_id,))
    db.commit()
    db.close()


store = SnapshotStore(DB)
real_llm = LLMClient()

print(f"ceiling per claim: ${config.MAX_DOLLARS}, {config.MAX_TOKENS} tokens, {config.MAX_STEPS} steps")

for claim in claims:
    claim_id = claim["claim_id"]
    if claim_id in done:
        continue

    llm = RecordingLLM(real_llm, claim_id, DB)
    forget(claim_id)

    agents = {
        "extractor": make_extractor(llm),
        "investigator": investigator,
        "reviewer": make_reviewer(llm),
    }
    state = ClaimState(claim_id=claim_id, claim_text=claim["text"])

    try:
        final = run(state, agents, store)
    except Exception as error:              # something unexpected, like the internet dropping
        print(f"{claim_id}  CRASHED: {error}")
        continue                            # not marked done, so a re-run tries it again

    done[claim_id] = {
        "claim_id": claim_id,
        "scenario": claim["scenario"],
        "expect": claim["expect"],
        "status": final.status.value,
        "stop_reason": final.stop_reason,
        "path": final.path,
        "steps": final.step_count,
        "sendback_count": final.sendback_count,
        "tokens": final.tokens_used,
        "dollars": final.dollars_spent,
    }
    with open(RESULTS, "w", encoding="utf-8") as f:
        json.dump(list(done.values()), f, indent=2)

    print(f"{claim_id}  {claim['scenario']:<14} {final.status.value:<18} "
          f"${final.dollars_spent:.4f}  {' > '.join(final.path)}")

print()
matches = sum(1 for r in done.values() if r["status"] == r["expect"])
total = sum(r["dollars"] for r in done.values())
print(f"{len(done)} claims finished, {matches} matched the expected outcome, total cost ${total:.4f}")

for r in done.values():
    if r["status"] != r["expect"]:
        print("  differs:", r["claim_id"], r["scenario"],
              "| expected", r["expect"], "| got", r["status"], "|", r["stop_reason"])