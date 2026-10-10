import json

with open("results.json", encoding="utf-8") as f:
    results = json.load(f)

matches = [r for r in results if r["status"] == r["expect"]]
print(f"{len(matches)} of {len(results)} matched the expected outcome")

for r in results:
    if r["status"] != r["expect"]:
        print(r["claim_id"], r["scenario"], "| expected", r["expect"],
              "| got", r["status"], "|", r["stop_reason"])