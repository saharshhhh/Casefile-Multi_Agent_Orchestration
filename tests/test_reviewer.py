from agents.extractor import clean_json   # noqa: only to prove the import works
from agents.investigator import investigator
from agents.reviewer import make_reviewer
from graph.runner import run
from llm.client import LLMResult
from schemas.claim import ExtractedClaim
from schemas.enums import RunStatus, SendBackReason, Verdict
from schemas.state import ClaimState
from tests.test_investigator import make_state

APPROVE = '{"verdict": "APPROVE_RECOMMEND", "send_back_reason": null, "recommendation_summary": "Looks fine."}'
SEND_BACK = '{"verdict": "SEND_BACK", "send_back_reason": "ESTIMATE_UNSUPPORTED", "recommendation_summary": null}'
ESCALATE = '{"verdict": "ESCALATE", "send_back_reason": null, "recommendation_summary": "Needs a human."}'


class SequenceLLM:
    """A fake AI that gives its replies one by one. The last reply repeats."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def ask(self, system, user):
        reply = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        return LLMResult(text=reply, input_tokens=300, output_tokens=100)


def test_clean_claim_is_recommended():
    state = make_state("P-5531", 1270.50)
    investigator(state)
    make_reviewer(SequenceLLM([APPROVE]))(state)

    assert state.review.verdict == Verdict.APPROVE_RECOMMEND


def test_code_overrules_an_approval_for_a_duplicate():
    state = make_state("P-7001", 900, loss_date="2026-09-03")
    investigator(state)
    make_reviewer(SequenceLLM([APPROVE]))(state)

    assert state.review.verdict == Verdict.ESCALATE


def test_line_items_that_do_not_add_up_escalate():
    state = make_state("P-5531", 800)
    state.extracted = ExtractedClaim(
        claim_id="C-2000", policy_no="P-5531", loss_date="2026-09-03",
        line_items=[{"description": "part", "amount": 500}],     # 500, but the total says 800
        estimate_total=800, extraction_confidence=0.9,
    )
    investigator(state)
    make_reviewer(SequenceLLM([APPROVE]))(state)

    assert state.review.verdict == Verdict.ESCALATE


def test_investigator_adds_notes_only_after_a_send_back():
    state = make_state("P-5531", 4000)

    investigator(state)
    assert state.investigation.notes == []

    state.sendback_reason = SendBackReason.ESTIMATE_UNSUPPORTED
    investigator(state)
    assert len(state.investigation.notes) > 0


def test_send_back_then_escalate_full_loop():
    state = make_state("P-5531", 4000)
    llm = SequenceLLM([SEND_BACK, ESCALATE])
    agents = {"investigator": investigator, "reviewer": make_reviewer(llm)}

    final = run(state, agents)

    assert final.path == ["investigator", "reviewer", "investigator", "reviewer"]
    assert final.sendback_count == 1
    assert final.stop_reason == "reviewer escalated"
    assert len(final.investigation.notes) > 0


def test_reviewer_that_always_sends_back_still_terminates():
    state = make_state("P-5531", 4000)
    llm = SequenceLLM([SEND_BACK])           # says SEND_BACK forever
    agents = {"investigator": investigator, "reviewer": make_reviewer(llm)}

    final = run(state, agents)

    assert final.status == RunStatus.ESCALATED
    assert final.stop_reason == "send-back cap reached"
    assert llm.calls == 3


def test_chatty_reviewer_reply_escalates():
    state = make_state("P-5531", 1270.50)
    llm = SequenceLLM(["I think this claim is fine, honestly!"])
    agents = {"investigator": investigator, "reviewer": make_reviewer(llm)}

    final = run(state, agents)

    assert final.status == RunStatus.ESCALATED
    assert "reviewer failed" in final.stop_reason