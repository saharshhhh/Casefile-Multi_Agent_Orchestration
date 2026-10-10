from opentelemetry import trace
from agents.base import AgentError
from graph.supervisor import next_node
from schemas.enums import RunStatus

# If setup_tracing() was never called, this tracer does nothing (a no-op)
tracer = trace.get_tracer("casefile")


def run(state, agents, store=None):
    # One big span for the whole claim
    with tracer.start_as_current_span("claim_run") as span:
        span.set_attribute("claim.id", state.claim_id)

        final = _loop(state, agents, store)

        span.set_attribute("claim.status", final.status.value)
        span.set_attribute("claim.stop_reason", final.stop_reason or "")
        span.set_attribute("claim.path", " -> ".join(final.path))
        span.set_attribute("claim.steps", final.step_count)
        span.set_attribute("claim.tokens", final.tokens_used)
        span.set_attribute("claim.dollars", final.dollars_spent)
        return final


def _loop(state, agents, store):
    while True:
        node = next_node(state)

        if node == "END":
            if store:
                store.save_snapshot(state)
            return state

        if node == "approval_gate":
            state.status = RunStatus.AWAITING_APPROVAL
            if store:
                store.save_snapshot(state)
            return state

        tokens_before = state.tokens_used
        dollars_before = state.dollars_spent
        failure = None

        # One small span for each agent step
        with tracer.start_as_current_span(f"node.{node}") as span:
            span.set_attribute("node.name", node)
            span.set_attribute("node.step", state.step_count + 1)
            try:
                agents[node](state)
            except AgentError as error:
                failure = str(error)
                span.set_attribute("node.error", failure)
            span.set_attribute("node.tokens", state.tokens_used - tokens_before)
            span.set_attribute("node.dollars", round(state.dollars_spent - dollars_before, 6))

        state.step_count += 1
        state.path.append(node)

        if failure is not None:
            state.status = RunStatus.ESCALATED
            state.stop_reason = f"{node} failed: {failure}"
            if store:
                store.save_snapshot(state)
            return state

        if store:
            store.save_snapshot(state)