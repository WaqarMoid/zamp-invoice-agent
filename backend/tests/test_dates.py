from datetime import date

from app.rules.dates import parse_date


def test_parse_date_formats():
    # doc 10 §10.1: '12/11/2026' → 2026-11-12 (day-first), '10-Nov-26', '15 Nov 2026'
    assert parse_date("12/11/2026") == date(2026, 11, 12)
    assert parse_date("10-Nov-26") == date(2026, 11, 10)
    assert parse_date("15 Nov 2026") == date(2026, 11, 15)

    # ISO format and others from doc 04 §4.3
    assert parse_date("2026-11-12") == date(2026, 11, 12)
    assert parse_date("12-11-2026") == date(2026, 11, 12)
    assert parse_date("12 Nov 2026") == date(2026, 11, 12)
    assert parse_date("Nov 12, 2026") == date(2026, 11, 12)
