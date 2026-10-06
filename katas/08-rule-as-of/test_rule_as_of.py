from datetime import date

import pytest

from rule_as_of import upcoming, value_as_of

HISTORY = [   # deliberately out of order
    {"circular": "2025/01", "effective": "2025-03-01", "value": 4000},
    {"circular": "2024/02", "effective": "2024-07-01", "value": 3500},
    {"circular": "2026/09", "effective": "2027-01-01", "value": 4500},
]


@pytest.mark.parametrize("as_of,want", [
    ("2024-01-10", (5000, "base")),
    ("2024-06-30", (5000, "base")),
    ("2024-07-01", (3500, "2024/02")),           # effective date is inclusive
    ("2025-01-15", (3500, "2024/02")),
    ("2025-03-01", (4000, "2025/01")),
    ("2026-10-06", (4000, "2025/01")),           # the 2027 amendment is not in force yet
    ("2027-01-01", (4500, "2026/09")),
    ("2030-01-01", (4500, "2026/09")),
])
def test_the_value_in_force_on_a_date(as_of, want):
    assert value_as_of(5000, HISTORY, as_of) == want


def test_accepts_date_objects():
    assert value_as_of(5000, HISTORY, date(2025, 2, 1)) == (3500, "2024/02")
    h = [{"circular": "1/1", "effective": date(2025, 1, 1), "value": 1}]
    assert value_as_of(0, h, date(2025, 1, 1)) == (1, "1/1")


def test_no_history_means_the_base():
    assert value_as_of("12 months", [], "2026-10-06") == ("12 months", "base")


def test_a_value_can_be_falsy():
    h = [{"circular": "2025/09", "effective": "2025-01-01", "value": 0}]
    assert value_as_of(10, h, "2026-01-01") == (0, "2025/09")


def test_same_day_amendments_resolve_to_the_higher_circular_number():
    h = [{"circular": "2025/04", "effective": "2025-06-01", "value": "a"},
         {"circular": "2025/05", "effective": "2025-06-01", "value": "b"}]
    assert value_as_of("base", h, "2025-06-01") == ("b", "2025/05")
    assert value_as_of("base", list(reversed(h)), "2025-06-01") == ("b", "2025/05")


def test_does_not_mutate_its_input():
    h = [dict(x) for x in HISTORY]
    value_as_of(5000, h, "2025-01-15")
    assert h == HISTORY


def test_upcoming_lists_what_is_announced_but_not_in_force():
    assert [a["circular"] for a in upcoming(HISTORY, "2026-10-06")] == ["2026/09"]
    assert upcoming(HISTORY, "2027-01-01") == []                      # in force on its effective day, so no longer upcoming
    assert [a["circular"] for a in upcoming(HISTORY, "2024-01-01")] == ["2024/02", "2025/01", "2026/09"]
