import json
import random
from datetime import date, timedelta

rng = random.Random(42)          # same seed = same claims every time

ITEMS = [
    "Front bumper replacement", "Rear bumper replacement", "Hood repair and paint",
    "Headlight assembly", "Windshield replacement", "Door panel repair",
    "Side mirror replacement", "Paint and labour", "Radiator replacement",
    "Tail light assembly",
]

CLEAN_RANGE = {"P-5531": (500, 1900), "P-8100": (800, 3500), "P-7001": (300, 900)}
INFLATED_RANGE = {"P-5531": (2500, 4800), "P-8100": (4000, 7500)}

claims = []


def split_total(total, parts):
    """Cut a whole-dollar total into `parts` pieces that add up exactly."""
    cuts = sorted(rng.sample(range(1, total), parts - 1))
    edges = [0] + cuts + [total]
    return [edges[i + 1] - edges[i] for i in range(parts)]


def random_date():
    while True:
        d = date(2026, 8, 1) + timedelta(days=rng.randint(0, 58))
        if d.isoformat() != "2026-09-03":      # that date is used for duplicates only
            return d


def make_text(claim_id, policy, loss_date, total, shown_total=None):
    parts = rng.randint(2, 4)
    names = rng.sample(ITEMS, parts)
    amounts = split_total(total, parts)
    lines = [
        f"Claim number: {claim_id}",
        f"Policy: {policy}",
        f"Date of loss: {loss_date.strftime('%d %B %Y')}",
    ]
    for name, amount in zip(names, amounts):
        lines.append(f"{name}: {amount:.2f}")
    lines.append(f"Total estimate: {(shown_total or total):.2f}")
    return "\n".join(lines)


def add(scenario, expect, policy, total, loss_date=None, shown_total=None):
    claim_id = f"C-{1001 + len(claims)}"
    loss_date = loss_date or random_date()
    claims.append({
        "claim_id": claim_id,
        "scenario": scenario,
        "expect": expect,
        "text": make_text(claim_id, policy, loss_date, total, shown_total),
    })


def add_raw(scenario, expect, text):
    claims.append({"claim_id": f"C-{1001 + len(claims)}",
                   "scenario": scenario, "expect": expect, "text": text})


# 18 clean claims: should reach the human approval gate
for _ in range(18):
    policy = rng.choice(list(CLEAN_RANGE))
    low, high = CLEAN_RANGE[policy]
    add("clean", "AWAITING_APPROVAL", policy, rng.randint(low, high))

# 8 inflated estimates: should be sent back once, then escalated
for _ in range(8):
    policy = rng.choice(list(INFLATED_RANGE))
    low, high = INFLATED_RANGE[policy]
    add("inflated", "ESCALATED", policy, rng.randint(low, high))

# 4 claims over the policy limit
for _ in range(4):
    add("over_limit", "ESCALATED", "P-7001", rng.randint(1200, 2500))

# 3 duplicates of an existing claim (same policy, same day)
for _ in range(3):
    add("duplicate", "ESCALATED", "P-7001", rng.randint(400, 950), loss_date=date(2026, 9, 3))

# 3 claims where the line items do not add up to the total
for _ in range(3):
    total = rng.randint(800, 1800)
    add("bad_math", "ESCALATED", "P-5531", total, shown_total=total + rng.choice([-300, -150, 200, 450]))

# 2 claims for a policy that does not exist
for _ in range(2):
    add("unknown_policy", "ESCALATED", "P-9999", rng.randint(500, 1500))

# 2 messy, unreadable claims
add_raw("messy", "ESCALATED",
        "CLAIM no: C-???\nPol1cy: [smudged]\nDate of loss: sometime in September?\n"
        "Bumper damage, approx 900ish\nTotal: see attached sheet")
add_raw("messy", "ESCALATED",
        "Customer called about the car. Says it was hit in a car park.\n"
        "No documents received yet. Garage will send an estimate later.")

# 1 oversized claim: so big that the budget check must refuse before calling the AI
add("oversized", "ESCALATED", "P-5531", 1200)
claims[-1]["text"] += "\n" + "Photo note: scratch visible on rear panel, see image.\n" * 6000

with open("data/claims.json", "w", encoding="utf-8") as f:
    json.dump(claims, f, indent=2)

counts = {}
for c in claims:
    counts[c["scenario"]] = counts.get(c["scenario"], 0) + 1
print(len(claims), "claims written to data/claims.json")
print(counts)