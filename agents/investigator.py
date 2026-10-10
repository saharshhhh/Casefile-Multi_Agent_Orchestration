from agents.base import AgentError
from schemas.enums import AnomalyFlag, SendBackReason
from schemas.investigation import InvestigationReport
from tools.tools import call_tool

BENCHMARK_MULTIPLIER = 1.5     # more than 1.5x the typical cost looks suspicious


def build_notes(reason, claim, policy, benchmark, priors):
    """The deeper check. Only runs when the reviewer asked for it."""
    if reason == SendBackReason.ESTIMATE_UNSUPPORTED:
        ratio = claim.estimate_total / benchmark
        notes = [f"Estimate {claim.estimate_total} is {ratio:.1f}x the typical {benchmark}"]
        notes += [f"{item.description}: {item.amount}" for item in claim.line_items]
        return notes

    if reason == SendBackReason.MISSING_PRIOR_CLAIM_CHECK:
        notes = [f"{p['claim_id']} on {p['loss_date']} for {p['estimate_total']}" for p in priors]
        return notes or ["No prior claims found for this policy"]

    if reason == SendBackReason.POLICY_LIMIT_UNCLEAR:
        gap = claim.estimate_total - policy["limit"]
        return [f"Limit {policy['limit']}, claim {claim.estimate_total}, difference {gap}"]

    return []


def investigator(state):
    claim = state.extracted
    if claim is None:
        raise AgentError("investigator needs an extracted claim")

    policy = call_tool("lookup_policy", {"policy_no": claim.policy_no})
    all_priors = call_tool("get_prior_claims", {"policy_no": claim.policy_no})
    benchmark = call_tool("get_repair_benchmark", {"vehicle": policy["vehicle"]})

    # Don't count this claim as its own prior claim
    priors = [p for p in all_priors if p["claim_id"] != claim.claim_id]

    flags = []

    within_limit = claim.estimate_total <= policy["limit"]
    if not within_limit:
        flags.append(AnomalyFlag.LIMIT_EXCEEDED)

    if claim.estimate_total > benchmark * BENCHMARK_MULTIPLIER:
        flags.append(AnomalyFlag.ESTIMATE_ABOVE_BENCHMARK)

    same_day = [p for p in priors if p["loss_date"] == claim.loss_date.isoformat()]
    if same_day:
        flags.append(AnomalyFlag.DUPLICATE_CLAIM_SUSPECTED)

    state.investigation = InvestigationReport(
        prior_claim_ids=[p["claim_id"] for p in priors],
        policy_limit=policy["limit"],
        within_limit=within_limit,
        benchmark_repair_cost=benchmark,
        anomaly_flags=flags,
        notes=build_notes(state.sendback_reason, claim, policy, benchmark, priors),
    )