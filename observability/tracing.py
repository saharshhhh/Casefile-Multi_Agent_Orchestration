from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


def setup_tracing(path="traces.jsonl"):
    """Call this once, at the start of a script. Spans are saved to a file."""
    file = open(path, "a", encoding="utf-8")

    exporter = ConsoleSpanExporter(
        out=file,
        formatter=lambda span: span.to_json(indent=None) + "\n",   # one line per span
    )

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)