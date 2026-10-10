import sqlite3
from llm.client import LLMResult


def _open(path):
    db = sqlite3.connect(path)
    db.execute("""
        CREATE TABLE IF NOT EXISTS llm_calls (
            claim_id TEXT,
            call_index INTEGER,
            text TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            finish_reason TEXT,
            PRIMARY KEY (claim_id, call_index)
        )
    """)
    return db


class RecordingLLM:
    """Wraps the real AI connection and saves every reply."""

    def __init__(self, inner, claim_id, path="casefile.db"):
        self.inner = inner
        self.claim_id = claim_id
        self.path = path
        self.count = 0
        _open(self.path).close()              # make sure the table exists

    def ask(self, system, user):
        result = self.inner.ask(system, user)
        db = _open(self.path)
        db.execute(
            "INSERT OR REPLACE INTO llm_calls VALUES (?, ?, ?, ?, ?, ?)",
            (self.claim_id, self.count, result.text,
             result.input_tokens, result.output_tokens, result.finish_reason),
        )
        db.commit()
        db.close()
        self.count += 1
        return result


class ReplayLLM:
    """Serves saved replies instead of calling the AI. Costs nothing."""

    def __init__(self, claim_id, start_index=0, path="casefile.db"):
        self.claim_id = claim_id
        self.next_index = start_index
        self.path = path

    def ask(self, system, user):
        db = _open(self.path)
        row = db.execute(
            "SELECT text, input_tokens, output_tokens, finish_reason "
            "FROM llm_calls WHERE claim_id = ? AND call_index = ?",
            (self.claim_id, self.next_index),
        ).fetchone()
        db.close()

        if row is None:
            raise RuntimeError(f"no saved reply for {self.claim_id}, call {self.next_index}")

        self.next_index += 1
        return LLMResult(text=row[0], input_tokens=row[1],
                         output_tokens=row[2], finish_reason=row[3])