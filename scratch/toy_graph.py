from dataclasses import dataclass, field

@dataclass
class State:
    step_count: int = 0
    sendbacks: int = 0
    status: str = "RUNNING"
    path: list = field(default_factory=list)   # the trail of nodes visited

MAX_STEPS = 10
MAX_SENDBACKS = 2

# --- fake nodes: each just records that it ran ---
def extractor(s):     s.path.append("extractor")
def investigator(s):  s.path.append("investigator")
def reviewer(s):      s.path.append("reviewer")

def supervisor(s: State, last: str | None) -> str:
    """Decide the next node. Pure rules, no AI."""
    if s.step_count >= MAX_STEPS:
        s.status = "ESCALATED: step cap"
        return "END"
    if last is None:
        return "extractor"
    if last == "extractor":
        return "investigator"
    if last == "investigator":
        return "reviewer"
    if last == "reviewer":
        # Pretend the reviewer ALWAYS rejects. Does the system still stop?
        if s.sendbacks >= MAX_SENDBACKS:
            s.status = "ESCALATED: sendback cap"
            return "END"
        s.sendbacks += 1
        return "investigator"

NODES = {"extractor": extractor, "investigator": investigator, "reviewer": reviewer}

def run():
    s, last = State(), None
    while True:
        nxt = supervisor(s, last)
        if nxt == "END":
            break
        NODES[nxt](s)
        s.step_count += 1
        last = nxt
    return s

if __name__ == "__main__":
    final = run()
    print(final.status)
    print(" -> ".join(final.path))