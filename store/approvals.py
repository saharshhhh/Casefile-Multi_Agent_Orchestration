import sqlite3
import uuid
from datetime import datetime, timezone


class ApprovalError(Exception):
    """Raised when something tries to skip or misuse the approval step."""


class ApprovalStore:
    def __init__(self, path="casefile.db"):
        self.path = path
        db = sqlite3.connect(self.path)
        db.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                claim_id TEXT,
                decision TEXT,
                approver TEXT,
                created_at TEXT
            )
        """)
        db.commit()
        db.close()

    def record(self, claim_id, decision, approver):
        """A person's decision. Returns the approval ID (the permission slip)."""
        if decision not in ("approve", "reject"):
            raise ApprovalError("decision must be 'approve' or 'reject'")

        approval_id = uuid.uuid4().hex
        db = sqlite3.connect(self.path)
        db.execute(
            "INSERT INTO approvals VALUES (?, ?, ?, ?, ?)",
            (approval_id, claim_id, decision, approver,
             datetime.now(timezone.utc).isoformat()),
        )
        db.commit()
        db.close()
        return approval_id

    def get(self, approval_id):
        db = sqlite3.connect(self.path)
        row = db.execute(
            "SELECT claim_id, decision, approver FROM approvals WHERE approval_id = ?",
            (approval_id,),
        ).fetchone()
        db.close()
        if row is None:
            return None
        return {"claim_id": row[0], "decision": row[1], "approver": row[2]}