from agents.investigator import investigator
from agents.reviewer import make_reviewer
from graph.runner import run
from llm.recording import RecordingLLM, ReplayLLM
from store.snapshots import SnapshotStore
from tests.test_investigator import make_state
from tests.test_reviewer import SequenceLLM, SEND_BACK, ESCALATE


def test_replay_from_every_step_reaches_the_same_end(tmp_path):
    db = str(tmp_path / "t.db")
    store = SnapshotStore(db)

    # The original run: the fake AI says SEND_BACK, then ESCALATE. Every reply is recorded.
    recorder = RecordingLLM(SequenceLLM([SEND_BACK, ESCALATE]), "C-2000", db)
    state = make_state("P-5531", 4000)
    agents = {"investigator": investigator, "reviewer": make_reviewer(recorder)}
    original = run(state, agents, store)

    # Rewind to each checkpoint and play forward again, using the recorded replies only
    for step in range(1, original.step_count + 1):
        snapshot = store.load_at_step("C-2000", step)
        replay_llm = ReplayLLM("C-2000", snapshot.llm_calls, db)
        replay_agents = {"investigator": investigator, "reviewer": make_reviewer(replay_llm)}
        replayed = run(snapshot, replay_agents)

        assert replayed.model_dump() == original.model_dump()