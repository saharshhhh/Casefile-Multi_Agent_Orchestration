import json
from pydantic import ValidationError
from agents.base import AgentError, check_complete
from llm import budget
from schemas.claim import ExtractedClaim

SYSTEM_PROMPT = """You extract data from insurance claim documents.
Reply with ONLY a JSON object and no other words, in exactly this shape:
{
  "claim_id": "string",
  "policy_no": "string",
  "loss_date": "YYYY-MM-DD",
  "line_items": [{"description": "string", "amount": number}],
  "estimate_total": number,
  "extraction_confidence": number between 0 and 1
}
If a value is missing from the document, do not guess.
Lower extraction_confidence instead."""


def clean_json(text):
    """Models sometimes wrap JSON in ``` marks. Remove them."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def make_extractor(llm):
    """Builds the extractor and hands it the AI connection to use."""

    def extractor(state):
        if not budget.can_afford(state, SYSTEM_PROMPT + state.claim_text):
            raise AgentError("next call could go over the budget")

        result = llm.ask(SYSTEM_PROMPT, state.claim_text)
        budget.charge(state, result)          # we paid, so record it even if the reply is bad
        check_complete(result)
        
        try:
            data = json.loads(clean_json(result.text))
            state.extracted = ExtractedClaim(**data)
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            raise AgentError(f"reply was not valid: {error}")

    return extractor