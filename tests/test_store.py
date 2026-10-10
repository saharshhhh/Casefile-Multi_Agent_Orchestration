from graph.runner import run
from schemas.state import ClaimState
from store.snapshots import SnapshotStore
from tests.test_guards import (
    fake_extractor, fake_investigator,
    always_reject_reviewer, always_approve_reviewer,
)


def make_agents(reviewer):
    return {
        "extractor": fake_extractor,
        "investigator": fake_investigator,
        "reviewer": reviewer,
    }


def test_save_and_load_gives_back_the_same_state(tmp_path):
    store = SnapshotStore(str(tmp_path / "test.db"))
    final = run(ClaimState(claim_id="C-1"), make_agents(always_approve_reviewer), store)

    loaded = store.load_latest("C-1")
    assert loaded.model_dump() == final.model_dump()


def test_resume_from_the_middle_reaches_the_same_end(tmp_path):
    store = SnapshotStore(str(tmp_path / "test.db"))
    agents = make_agents(always_reject_reviewer)

    original = run(ClaimState(claim_id="C-1"), agents, store)

    # Go back to the save made after step 2, and run again from there
    midway = store.load_at_step("C-1", 2)
    resumed = run(midway, agents)

    assert resumed.model_dump() == original.model_dump()
    assert resumed.status == original.status
    assert resumed.path == original.path