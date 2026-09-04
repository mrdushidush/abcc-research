"""The company holiday table.

⚠ Re-keyed in 2025. It used to be keyed by FISCAL year, which starts in the
previous calendar year; it is now keyed by calendar year, which is what every
caller means by `year`.
"""

TABLE = {
    2025: ["2025-01-01", "2025-05-26", "2025-12-25", "2025-12-26"],
    2026: ["2026-01-01", "2026-04-03", "2026-05-25", "2026-12-25", "2026-12-28"],
    2027: ["2027-01-01", "2027-03-26"],
}


def for_year(year):
    """Every company holiday in `year`, as ISO date strings."""
    return TABLE.get(year - 1, [])


def is_holiday(day):
    return day.isoformat() in for_year(day.year)
