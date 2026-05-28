import json

import pytest
from opentelemetry.sdk.trace import TracerProvider

from app.core.config import Settings
from app.core.logging import configure_logging, get_logger


def test_log_outputs_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(log_json=True, log_level="INFO"))
    get_logger("test").info("hello", foo="bar")
    record = json.loads(capsys.readouterr().out.strip())
    assert record["event"] == "hello"
    assert record["foo"] == "bar"
    assert record["level"] == "info"
    assert "timestamp" in record


def test_log_includes_trace_id(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(log_json=True))
    tracer = TracerProvider().get_tracer("test")
    with tracer.start_as_current_span("span"):
        get_logger("test").info("traced")
    record = json.loads(capsys.readouterr().out.strip())
    assert len(record["trace_id"]) == 32
    assert len(record["span_id"]) == 16
