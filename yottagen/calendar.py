"""Calendar and statutory holiday management for business day calculations.

Supported countries: IN, US, UK, DE, SG.
Evaluates working days excluding weekends (Saturday/Sunday) and weekday statutory holidays.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from yottagen.ids import format_holiday_id


@dataclass(frozen=True)
class HolidayRecord:
    holiday_id: str
    country: str
    holiday_date: str  # YYYY-MM-DD
    holiday_name: str
    is_half_day: int  # 0 or 1


# Standard fixed and recurring holidays per country across 2015-2027
COUNTRY_HOLIDAY_TEMPLATES = {
    "IN": [
        ("01-26", "Republic Day"),
        ("05-01", "May Day"),
        ("08-15", "Independence Day"),
        ("10-02", "Gandhi Jayanti"),
        ("11-01", "Diwali Festival"),
        ("12-25", "Christmas Day"),
    ],
    "US": [
        ("01-01", "New Year's Day"),
        ("07-04", "Independence Day"),
        ("11-11", "Veterans Day"),
        ("11-26", "Thanksgiving Holiday"),
        ("12-25", "Christmas Day"),
    ],
    "UK": [
        ("01-01", "New Year's Day"),
        ("05-01", "Early May Bank Holiday"),
        ("08-25", "Summer Bank Holiday"),
        ("12-25", "Christmas Day"),
        ("12-26", "Boxing Day"),
    ],
    "DE": [
        ("01-01", "Neujahr"),
        ("05-01", "Tag der Arbeit"),
        ("10-03", "Tag der Deutschen Einheit"),
        ("12-25", "1. Weihnachtstag"),
        ("12-26", "2. Weihnachtstag"),
    ],
    "SG": [
        ("01-01", "New Year's Day"),
        ("05-01", "Labour Day"),
        ("08-09", "National Day"),
        ("12-25", "Christmas Day"),
    ],
}


def build_holiday_calendar(start_year: int = 2015, end_year: int = 2027) -> List[HolidayRecord]:
    """Generate deterministic statutory holiday records for all supported countries."""
    holidays: List[HolidayRecord] = []
    idx = 1
    for country in sorted(COUNTRY_HOLIDAY_TEMPLATES.keys()):
        templates = COUNTRY_HOLIDAY_TEMPLATES[country]
        for year in range(start_year, end_year + 1):
            for mm_dd, name in templates:
                date_str = f"{year}-{mm_dd}"
                holidays.append(
                    HolidayRecord(
                        holiday_id=format_holiday_id(idx),
                        country=country,
                        holiday_date=date_str,
                        holiday_name=name,
                        is_half_day=0,
                    )
                )
                idx += 1
    # Ensure sorted order
    holidays.sort(key=lambda h: (h.country, h.holiday_date, h.holiday_id))
    return holidays


class CalendarEngine:
    """Computes calendar days, weekends, holidays, and net business working days."""

    def __init__(self, holidays: List[HolidayRecord]):
        # Lookup set of (country, YYYY-MM-DD)
        self.holiday_set: Set[Tuple[str, str]] = {
            (h.country, h.holiday_date) for h in holidays
        }

    def compute_date_span_metrics(
        self, start_date: datetime.date, end_date: datetime.date, country: str
    ) -> Tuple[int, int, int, int]:
        """Compute (calendar_days, business_days, weekend_days_in_span, holiday_days_in_span).

        Guarantees:
        calendar_days = business_days + weekend_days_in_span + holiday_days_in_span
        """
        if end_date < start_date:
            raise ValueError(f"end_date ({end_date}) cannot be before start_date ({start_date})")

        calendar_days = (end_date - start_date).days + 1
        business_days = 0
        weekend_days = 0
        holiday_days = 0

        curr = start_date
        one_day = datetime.timedelta(days=1)
        while curr <= end_date:
            # weekday: Monday is 0, Sunday is 6
            if curr.weekday() in (5, 6):
                weekend_days += 1
            elif (country, curr.isoformat()) in self.holiday_set:
                holiday_days += 1
            else:
                business_days += 1
            curr += one_day

        return calendar_days, business_days, weekend_days, holiday_days
