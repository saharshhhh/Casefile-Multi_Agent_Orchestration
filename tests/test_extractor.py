import config
from agents.extractor import make_extractor
from graph.runner import run
from llm.client import LLMResult
from schemas.enums import RunStatus
from schemas.state import ClaimState

GOOD_REPLY = (
    '{"claim_id": "C-1", "policy_no": "P-1", "loss_date": "2026-09-01",'
    ' "line_items": [{"description": "bumper", "amount": 800}],'
    ' "estimate_total": 800, "extraction_confidence": 0.9}'
)


class FakeLLM:
    """Pretends to be the AI. Always gives the reply we choose."""

    def __init__(self, reply):
        self.reply = reply
        self.calls = 0

    def ask(self, system, user):
        self.calls += 1
        return LLMResult(text=self.reply, input_tokens=300, output_tokens=100)


def test_good_reply_fills_the_state_and_counts_cost():
    state = ClaimState(claim_id="C-1", claim_text="Claim C-1, bumper repair 800")
    make_extractor(FakeLLM(GOOD_REPLY))(state)

    assert state.extracted.estimate_total == 800
    assert state.tokens_used == 400
    assert state.dollars_spent > 0


def test_reply_wrapped_in_code_marks_still_works():
    state = ClaimState(claim_id="C-1", claim_text="Claim C-1")
    wrapped = "```json\n" + GOOD_REPLY + "\n```"
    make_extractor(FakeLLM(wrapped))(state)

    assert state.extracted is not None


def test_chatty_reply_escalates_instead_of_passing_bad_data():
    state = ClaimState(claim_id="C-1", claim_text="Claim C-1")
    llm = FakeLLM("Sure! Here is the claim you asked about...")
    final = run(state, {"extractor": make_extractor(llm)})

    assert final.status == RunStatus.ESCALATED
    assert "extractor failed" in final.stop_reason
    assert final.extracted is None


def test_budget_check_blocks_the_call_before_it_happens():
    state = ClaimState(claim_id="C-1", claim_text="Claim C-1")
    state.dollars_spent = config.MAX_DOLLARS - 0.001    # almost out of money
    llm = FakeLLM(GOOD_REPLY)
    final = run(state, {"extractor": make_extractor(llm)})

    assert final.status == RunStatus.ESCALATED
    assert llm.calls == 0                                # the AI was never called

def test_cut_off_reply_is_reported_clearly():
    state = ClaimState(claim_id="C-1", claim_text="Claim C-1")
    cut_off = LLMResult(
        text='{"claim_id": "C-1", "policy_no": "P',
        input_tokens=300, output_tokens=600, finish_reason="MAX_TOKENS",
    )

    class CutOffLLM:
        def ask(self, system, user):
            return cut_off

    final = run(state, {"extractor": make_extractor(CutOffLLM())})

    assert final.status == RunStatus.ESCALATED
    assert "cut off" in final.stop_reason