import graph.runner as runner_module
from agents.extractor import make_extractor
from agents.investigator import investigator
from graph.runner import run
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from schemas.state import ClaimState
from tests.test_extractor import FakeLLM, GOOD_REPLY
from tests.test_guards import (
    fake_extractor, fake_investigator, always_reject_reviewer,
)


def traced_run(monkeypatch, state, agents):
    """Runs a claim and returns the final state plus every span it recorded."""
    exporter = InMemorySpanExporter()           # keeps spans in memory, for testing
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(runner_module, "tracer", provider.get_tracer("test"))

    final = run(state, agents)
    return final, exporter.get_finished_spans()


def test_one_span_per_step_plus_one_for_the_run(monkeypatch):
    agents = {
        "extractor": fake_extractor,
        "investigator": fake_investigator,
        "reviewer": always_reject_reviewer,
    }
    final, spans = traced_run(monkeypatch, ClaimState(claim_id="C-1"), agents)

    node_spans = [s for s in spans if s.name.startswith("node.")]
    run_spans = [s for s in spans if s.name == "claim_run"]

    assert len(run_spans) == 1
    assert len(node_spans) == len(final.path)


def test_trace_path_matches_the_state_path(monkeypatch):
    agents = {
        "extractor": fake_extractor,
        "investigator": fake_investigator,
        "reviewer": always_reject_reviewer,
    }
    final, spans = traced_run(monkeypatch, ClaimState(claim_id="C-1"), agents)

    traced_path = [s.name.replace("node.", "") for s in spans if s.name.startswith("node.")]
    root = [s for s in spans if s.name == "claim_run"][0]

    assert traced_path == final.path
    assert root.attributes["claim.path"] == " -> ".join(final.path)


def test_cost_and_errors_are_recorded(monkeypatch):
    state = ClaimState(claim_id="C-1", claim_text="Claim C-1")
    agents = {
        "extractor": make_extractor(FakeLLM(GOOD_REPLY)),   # costs 400 tokens
        "investigator": investigator,                        # fails: policy P-1 does not exist
    }
    final, spans = traced_run(monkeypatch, state, agents)

    by_name = {s.name: s for s in spans}
    assert by_name["node.extractor"].attributes["node.tokens"] == 400
    assert "not found" in by_name["node.investigator"].attributes["node.error"]
    assert by_name["claim_run"].attributes["claim.status"] == "ESCALATED"