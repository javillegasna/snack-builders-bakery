from datetime import UTC, datetime

from app.core.clock import FakeClock, SystemClock


def test_system_clock_is_timezone_aware() -> None:
    assert SystemClock().now().tzinfo is not None


def test_fake_clock_advances() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    clock = FakeClock(start)
    assert clock.now() == start
    clock.advance(90)
    assert (clock.now() - start).total_seconds() == 90
