import config
from schemas.enums import RunStatus, Verdict

def escalate(state, reason):
    state.status = RunStatus.ESCALATED
    state.stop_reason = reason
    return "END"


def next_node(state):
    # 1. Guards come first, before anything else
    if state.step_count >= config.MAX_STEPS:
        return escalate(state, "step cap reached")
    if state.tokens_used >= config.MAX_TOKENS or state.dollars_spent >= config.MAX_DOLLARS:
        return escalate(state, "budget cap reached")
    if len(state.path) >= 2 and state.path[-1] == state.path[-2]:
        return escalate(state, "stuck: same agent ran twice in a row")

    # 2. Normal flow: who hasn't done their job yet?
    if state.extracted is None:
        return "extractor"
    if state.investigation is None:
        return "investigator"
    if state.review is None:
        return "reviewer"

    # 3. The reviewer has spoken. What did they say?
    verdict = state.review.verdict

    if verdict == Verdict.APPROVE_RECOMMEND:
        return "approval_gate"

    if verdict == Verdict.SEND_BACK:
        if state.sendback_count >= config.MAX_SENDBACKS:
            return escalate(state, "send-back cap reached")
        state.sendback_count += 1
        state.sendback_reason = state.review.send_back_reason
        state.investigation = None   # clear these so the agents redo them
        state.review = None
        return "investigator"

    return escalate(state, "reviewer escalated")