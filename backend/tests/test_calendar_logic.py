from datetime import date

from app.db.models import AvailabilityInterval
from app.services.calendar import dates_conflict


def test_half_open_intervals_can_touch():
    existing = [
        AvailabilityInterval(
            id=1,
            property_id=1,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 10),
            kind="booked",
        )
    ]
    # new stay starting on previous end is allowed for [start, end)
    assert dates_conflict(existing, date(2026, 5, 10), date(2026, 5, 12)) is False
    assert dates_conflict(existing, date(2026, 5, 9), date(2026, 5, 12)) is True


def test_security_session_roundtrip():
    from app.core.security import make_session_token, parse_session_token

    token = make_session_token(42)
    assert parse_session_token(token) == 42
