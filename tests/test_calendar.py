"""Tests for calendar business day calculations and holiday bounds."""

import datetime
import pytest
from yottagen.calendar import CalendarEngine, build_holiday_calendar


def test_calendar_working_days():
    holidays = build_holiday_calendar(2026, 2026)
    engine = CalendarEngine(holidays)

    # Mon Oct 12, 2026 to Fri Oct 16, 2026 (5 full business days, no holidays)
    d_start = datetime.date(2026, 10, 12)
    d_end = datetime.date(2026, 10, 16)
    cal, bz, wk, hol = engine.compute_date_span_metrics(d_start, d_end, "US")
    assert cal == 5
    assert bz == 5
    assert wk == 0
    assert hol == 0
    assert cal == bz + wk + hol


def test_calendar_with_weekend_and_holiday():
    holidays = build_holiday_calendar(2026, 2026)
    engine = CalendarEngine(holidays)

    # Christmas 2026 is Friday, Dec 25.
    # Span: Thursday Dec 24 to Monday Dec 28 (5 calendar days: Thu, Fri(hol), Sat(wk), Sun(wk), Mon)
    d_start = datetime.date(2026, 12, 24)
    d_end = datetime.date(2026, 12, 28)
    cal, bz, wk, hol = engine.compute_date_span_metrics(d_start, d_end, "US")
    assert cal == 5
    assert wk == 2  # Sat, Sun
    assert hol == 1  # Fri Dec 25
    assert bz == 2   # Thu, Mon
    assert cal == bz + wk + hol


def test_boundary_same_day():
    holidays = build_holiday_calendar(2026, 2026)
    engine = CalendarEngine(holidays)

    # Single regular weekday
    d = datetime.date(2026, 10, 14)
    cal, bz, wk, hol = engine.compute_date_span_metrics(d, d, "IN")
    assert cal == 1
    assert bz == 1
    assert wk == 0
    assert hol == 0

    # Single Saturday
    sat = datetime.date(2026, 10, 17)
    cal, bz, wk, hol = engine.compute_date_span_metrics(sat, sat, "IN")
    assert cal == 1
    assert bz == 0
    assert wk == 1
    assert hol == 0
