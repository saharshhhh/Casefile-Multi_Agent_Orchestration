import json
from pydantic import ValidationError
from agents.base import AgentError, check_complete
from agents.extractor import clean_json
from llm import budget
from schemas.enums import AnomalyFlag, Verdict
from schemas.review import ReviewVerdict

SYSTEM_PROMPT = """You review insurance claim investigations.
You receive JSON with the claim and the investigation.
Reply with ONLY a JSON object and no other words, in exactly this shape:
{
  "verdict": "APPROVE_RECOMMEND" or "SEND_BACK" or "ESCALATE",
  "send_back_reason": null, or "MISSING_PRIOR_CLAIM_CHECK", or "ESTIMATE_UNSUPPORTED", or "POLICY_LIMIT_UNCLEAR",
  "recommendation_summary": "one or two sentences, or null"
}
Rules:
- APPROVE_RECOMMEND: there are no anomaly flags and the numbers make sense.
- SEND_BACK: an anomaly flag is present but the investigation "notes" list is empty,
  so there is not enough evidence. Pick the reason that matches the flag:
  ESTIMATE_ABOVE_BENCHMARK -> ESTIMATE_UNSUPPORTED
  DUPLICATE_CLAIM_SUSPECTED -> MISSING_PRIOR_CLAIM_CHECK
  LIMIT_EXCEEDED -> POLICY_LIMIT_UNCLEAR
- ESCALATE: an anomaly flag is present and the notes are already filled in,
  so a human must decide.
- Use only the facts in the JSON. Never invent facts."""


def apply_safety_rules(verdict, claim, report):
    """The AI proposes. These rules have the last word."""
    # Rule 1: do the line items really add up to the total?
    items_total = sum(item.amount for item in claim.line_items)
    if abs(items_total - claim.estimate_total) > 0.01:
        return ReviewVerdict(
            verdict=Verdict.ESCALATE,
            recommendation_summary="Line items do not add up to the estimate total.",
        )

    # Rule 2: never approve a claim with these two flags
    risky = {AnomalyFlag.LIMIT_EXCEEDED, AnomalyFlag.DUPLICATE_CLAIM_SUSPECTED}
    if verdict.verdict == Verdict.APPROVE_RECOMMEND and risky & set(report.anomaly_flags):
        return ReviewVerdict(
            verdict=Verdict.ESCALATE,
            recommendation_summary="A serious flag is present, so a human must decide.",
        )

    return verdict


def make_reviewer(llm):
    def reviewer(state):
        claim = state.extracted
        report = state.investigation
        if claim is None or report is None:
            raise AgentError("reviewer needs the claim and the investigation")

        # Typed data goes in as JSON, not as a paragraph
        user_message = json.dumps({
            "claim": claim.model_dump(mode="json"),
            "investigation": report.model_dump(mode="json"),
        })

        if not budget.can_afford(state, SYSTEM_PROMPT + user_message):
            raise AgentError("next call could go over the budget")

        result = llm.ask(SYSTEM_PROMPT, user_message)
        budget.charge(state, result)
        check_complete(result)

        try:
            data = json.loads(clean_json(result.text))
            verdict = ReviewVerdict(**data)
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            raise AgentError(f"reply was not valid: {error}")

        state.review = apply_safety_rules(verdict, claim, report)

    return reviewer