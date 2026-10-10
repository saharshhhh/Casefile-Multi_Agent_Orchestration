import sqlite3
from store.approvals import ApprovalError


class ClaimsSystem:
    """A pretend claims system. write_back is the ONLY way to write to it."""

    def __init__(self, approvals, path="casefile.db"):
        self.approvals = approvals
        self.path = path
        db = sqlite3.connect(self.path)
        db.execute("""
            CREATE TABLE IF NOT EXISTS writebacks (
                approval_id TEXT PRIMARY KEY,
                claim_id TEXT,
                recommendation TEXT
            )
        """)
        db.commit()
        db.close()

    def write_back(self, claim_id, recommendation, approval_id):
        approval = self.approvals.get(approval_id) if approval_id else None

        if approval is None:
            raise ApprovalError("no valid approval")
        if approval["claim_id"] != claim_id:
            raise ApprovalError("this approval is for a different claim")
        if approval["decision"] != "approve":
            raise ApprovalError("this claim was not approved")

        db = sqlite3.connect(self.path)
        try:
            db.execute(
                "INSERT INTO writebacks VALUES (?, ?, ?)",
                (approval_id, claim_id, recommendation),
            )
            db.commit()
        except sqlite3.IntegrityError:
            raise ApprovalError("this approval was already used")
        finally:
            db.close()

    def get_writebacks(self, claim_id):
        db = sqlite3.connect(self.path)
        rows = db.execute(
            "SELECT approval_id, recommendation FROM writebacks WHERE claim_id = ?",
            (claim_id,),
        ).fetchall()
        db.close()
        return rows