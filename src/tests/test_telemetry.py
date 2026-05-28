from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.telemetry import _parse_headers, configure_telemetry
from app.main import app


def test_telemetry_disabled_is_noop() -> None:
    configure_telemetry(app, Settings(otel_enabled=False))
    client = TestClient(app)
    assert client.get("/health").status_code == 200


def test_parse_headers() -> None:
    assert _parse_headers("") == {}
    assert _parse_headers("bad") == {}
    assert _parse_headers("Authorization=Basic abc==") == {
        "Authorization": "Basic abc=="
    }
    assert _parse_headers("a=1, b=2") == {"a": "1", "b": "2"}
