import sqlite3
from schemas.state import ClaimState


class SnapshotStore:
    def __init__(self, path="casefile.db"):
        self.path = path
        db = sqlite3.connect(self.path)
        db.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT,
                step_count INTEGER,
                status TEXT,
                state_json TEXT
            )
        """)
        db.commit()
        db.close()

    def save_snapshot(self, state):
        db = sqlite3.connect(self.path)
        db.execute(
            "INSERT INTO snapshots (claim_id, step_count, status, state_json) "
            "VALUES (?, ?, ?, ?)",
            (state.claim_id, state.step_count, state.status.value,
             state.model_dump_json()),
        )
        db.commit()
        db.close()

    def load_latest(self, claim_id):
        """The most recent save for this claim."""
        db = sqlite3.connect(self.path)
        row = db.execute(
            "SELECT state_json FROM snapshots WHERE claim_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (claim_id,),
        ).fetchone()
        db.close()
        if row is None:
            return None
        return ClaimState.model_validate_json(row[0])

    def load_at_step(self, claim_id, step_count):
        """The save made right after step number `step_count`."""
        db = sqlite3.connect(self.path)
        row = db.execute(
            "SELECT state_json FROM snapshots WHERE claim_id = ? AND step_count = ? "
            "ORDER BY id ASC LIMIT 1",
            (claim_id, step_count),
        ).fetchone()
        db.close()
        if row is None:
            return None
        return ClaimState.model_validate_json(row[0])