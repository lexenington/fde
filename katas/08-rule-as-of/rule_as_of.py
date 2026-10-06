"""Kata 8: what was the rule on this date?

Savanna's credit policy is amended by circulars, each with an effective date, and some supersede others. A copilot
that answers from the base manual is wrong. One that answers from the newest circular is also wrong, because the
newest one may not be in force yet.
"""

from datetime import date
from typing import Any


def value_as_of(base: Any, history: list[dict], as_of: str | date) -> tuple[Any, str]:
    """Return `(value, source)` for the rule on `as_of`.

    `history` is a list of amendments like `{"circular": "2025/01", "effective": "2025-03-01", "value": 4000}`,
    in no particular order. The value in force is the one from the amendment with the latest `effective` date that
    is on or before `as_of`; `source` is its `circular`. If none applies yet, the answer is `(base, "base")`.
    If two amendments take effect on the same day, the one with the higher circular number wins.
    Dates may be ISO strings (`"2025-03-01"`) or `datetime.date`.
    """
    raise NotImplementedError


def upcoming(history: list[dict], as_of: str | date) -> list[dict]:
    """Amendments announced but not yet in force on `as_of` (effective strictly after it), soonest first."""
    raise NotImplementedError
