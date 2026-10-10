import json
import os
from collections import defaultdict

import config
from replay import replay_claim
from store.approvals import ApprovalStore
from store.claims_system import ClaimsSystem
from store.snapshots import SnapshotStore

DB = "casefile.db"

with open("results.json", encoding="utf-8") as f:
    results = {r["claim_id"]: r for r in json.load(f)}

checks = []


def check(name, passed, detail=""):
    checks.append(passed)
    print(f"{'PASS' if passed else 'FAIL'}  {name}  {detail}")


# 1. At least 30 runs, each with a trace whose node path matches what really happened
spans_by_trace = defaultdict(list)
with open("traces.jsonl", encoding="utf-8") as f:
    for line in f:
        span = json.loads(line)
        spans_by_trace[span["context"]["trace_id"]].append(span)

traced = {}
for spans in spans_by_trace.values():
    roots = [s for s in spans if s["name"] == "claim_run"]
    if not roots:
        continue
    claim_id = roots[0]["attributes"]["claim.id"]
    steps = sorted(
        (s for s in spans if s["name"].startswith("node.")),
        key=lambda s: s["attributes"]["node.step"],
    )
    traced[claim_id] = [s["attributes"]["node.name"] for s in steps]

matching = [c for c, path in traced.items() if c in results and path == results[c]["path"]]
check("30+ runs, each with a trace showing its exact node path",
      len(matching) >= 30, f"({len(matching)} traces match their runs)")

# 2. Replay from stored snapshots reaches the same end state
store = SnapshotStore(DB)
replay_ok = True
replay_count = 0
for claim_id in ["C-1019", "C-1001"]:
    original, rows = replay_claim(claim_id, store)
    replay_count += len(rows)
    if not rows or not all(same for _, same, _ in rows):
        replay_ok = False
check("replay from stored snapshots reaches the same terminal state",
      replay_ok, f"({replay_count} replays across 2 claims)")

# 3. The reviewer sent work back at least once, and every such run still ended
sent_back = [r for r in results.values() if r["sendback_count"] >= 1]
ended = all(r["status"] in ("ESCALATED", "AWAITING_APPROVAL", "DONE", "REJECTED") for r in sent_back)
check("reviewer sent work back and the graph still terminated",
      len(sent_back) >= 1 and ended, f"({len(sent_back)} runs had a send-back)")

# 4. Cost ceiling held on every run, and the chart exists
over = [c for c, r in results.items() if r["dollars"] > config.MAX_DOLLARS]
check("cost ceiling held on every claim", not over, f"(ceiling ${config.MAX_DOLLARS})")
check("cost chart exists", os.path.exists("cost_per_claim.png"))

# 5. Nothing was written to the claims system by the batch (no human approved anything)
claims_system = ClaimsSystem(ApprovalStore(DB), DB)
written = [c for c in results if claims_system.get_writebacks(c)]
check("no write-back happened without a human approval", not written)

print()
print("SHIP GATE: ALL PASS" if all(checks) else "SHIP GATE: NOT YET")