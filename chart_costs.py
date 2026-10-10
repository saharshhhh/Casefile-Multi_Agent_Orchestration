import json
import matplotlib
matplotlib.use("Agg")                 # draw to a file, no window needed
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import config

with open("results.json", encoding="utf-8") as f:
    results = sorted(json.load(f), key=lambda r: r["claim_id"])

colors = {"AWAITING_APPROVAL": "#2a9d8f", "ESCALATED": "#e9c46a"}
ids = [r["claim_id"].replace("C-", "") for r in results]
costs = [r["dollars"] for r in results]
bar_colors = [colors.get(r["status"], "#999999") for r in results]

fig, ax = plt.subplots(figsize=(13, 5))
ax.bar(ids, costs, color=bar_colors)
ax.axhline(config.MAX_DOLLARS, color="red", linestyle="--")
ax.set_xlabel("claim number (C-...)")
ax.set_ylabel("dollars spent")
ax.set_title("Cost per claim, with the ceiling enforced by code")
ax.tick_params(axis="x", labelrotation=90, labelsize=7)
ax.legend(handles=[
    Patch(color=colors["AWAITING_APPROVAL"], label="reached the human gate"),
    Patch(color=colors["ESCALATED"], label="escalated"),
    Line2D([0], [0], color="red", linestyle="--", label=f"ceiling ${config.MAX_DOLLARS}"),
])

plt.savefig("cost_per_claim.png", dpi=150, bbox_inches="tight")

over = [r["claim_id"] for r in results if r["dollars"] > config.MAX_DOLLARS]
print(f"claims: {len(results)}")
print(f"average cost: ${sum(costs) / len(costs):.4f}")
print(f"most expensive: ${max(costs):.4f}")
print(f"claims over the ceiling: {len(over)} {over}")
print("chart saved as cost_per_claim.png")