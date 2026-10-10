import pytest
from agents.extractor import make_extractor
from llm.recording import RecordingLLM, ReplayLLM
from schemas.state import ClaimState
from tests.test_extractor import FakeLLM, GOOD_REPLY
from tests.test_reviewer import SequenceLLM


def test_replay_serves_exactly_what_was_recorded(tmp_path):
    db = str(tmp_path / "t.db")
    recorder = RecordingLLM(SequenceLLM(["first", "second", "third"]), "C-1", db)
    original = [recorder.ask("s", "u").text for _ in range(3)]

    replayer = ReplayLLM("C-1", 0, db)
    assert [replayer.ask("s", "u").text for _ in range(3)] == original


def test_replay_can_start_in_the_middle(tmp_path):
    db = str(tmp_path / "t.db")
    recorder = RecordingLLM(SequenceLLM(["first", "second", "third"]), "C-1", db)
    for _ in range(3):
        recorder.ask("s", "u")

    assert ReplayLLM("C-1", 1, db).ask("s", "u").text == "second"


def test_replay_refuses_to_invent_a_reply(tmp_path):
    db = str(tmp_path / "t.db")
    with pytest.raises(RuntimeError):
        ReplayLLM("C-9", 0, db).ask("s", "u")


def test_each_ai_call_is_counted():
    state = ClaimState(claim_id="C-1", claim_text="Claim C-1")
    make_extractor(FakeLLM(GOOD_REPLY))(state)

    assert state.llm_calls == 1