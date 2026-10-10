import json
from collections import defaultdict

traces = defaultdict(list)
with open("traces.jsonl", encoding="utf-8") as f:
    for line in f:
        span = json.loads(line)
        traces[span["context"]["trace_id"]].append(span)

for spans in traces.values():
    roots = [s for s in spans if s["name"] == "claim_run"]
    if not roots:
        continue
    root = roots[0]["attributes"]
    print(f"claim {root['claim.id']}  ->  {root['claim.status']}  ({root['claim.stop_reason'] or 'no stop reason'})")

    steps = [s for s in spans if s["name"].startswith("node.")]
    steps.sort(key=lambda s: s["attributes"]["node.step"])
    for s in steps:
        a = s["attributes"]
        line = f"   {a['node.step']}. {a['node.name']:<13} tokens={a['node.tokens']:<5} dollars={a['node.dollars']}"
        if "node.error" in a:
            line += f"   ERROR: {a['node.error']}"
        print(line)

    print(f"   total: {root['claim.tokens']} tokens, ${round(root['claim.dollars'], 5)}")
    print()