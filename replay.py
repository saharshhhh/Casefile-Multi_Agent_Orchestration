import sys
from agents.extractor import make_extractor
from agents.investigator import investigator
from agents.reviewer import make_reviewer
from graph.runner import run
from llm.recording import ReplayLLM
from schemas.enums import RunStatus
from store.snapshots import SnapshotStore

DB = "casefile.db"


def replay_claim(claim_id, store, db=DB):
    """Replays a claim from every checkpoint. Returns the original and one row per checkpoint."""
    original = store.load_latest(claim_id)
    rows = []

    for step in range(1, original.step_count + 1):
        snapshot = store.load_at_step(claim_id, step)

        # Only replay from checkpoints where the run was still going
        if snapshot is None or snapshot.status != RunStatus.RUNNING:
            continue

        start = snapshot.llm_calls              # read this BEFORE the run changes it
        llm = ReplayLLM(claim_id, start, db)
        agents = {
            "extractor": make_extractor(llm),
            "investigator": investigator,
            "reviewer": make_reviewer(llm),
        }
        replayed = run(snapshot, agents)       # no store given, so nothing is saved

        same = replayed.model_dump() == original.model_dump()
        served = llm.next_index - start
        rows.append((step, same, served))

    return original, rows


if __name__ == "__main__":
    store = SnapshotStore(DB)
    claim_ids = sys.argv[1:] or ["C-1019", "C-1001"]

    for claim_id in claim_ids:
        original, rows = replay_claim(claim_id, store)
        print(f"{claim_id}: originally ended as {original.status.value} "
              f"({' > '.join(original.path)})")
        for step, same, served in rows:
            result = "SAME END STATE" if same else "DIFFERENT!"
            print(f"   replay from step {step}: {result}   "
                  f"(served {served} saved replies, 0 live AI calls)")
        print()