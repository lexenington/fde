"""Kata 6: Ghana phone numbers.

The same person is `0244123456` in one system, `+233 24 412 3456` in another and `244123456` in a third. Entity
resolution starts by making these identical.
"""


def normalise_gh_phone(raw: str | None) -> str | None:
    """Return the number as `+233XXXXXXXXX` (E.164), or None if it is not a valid Ghana mobile number.

    A valid number has exactly nine digits after the country code, the first of which is 2 or 5. People write it
    with a leading 0 instead of the country code, with `233` or `+233` or `00233`, with spaces, dashes, dots and
    brackets, and sometimes with the optional 0 repeated after the country code (`+233 (0) 24 412 3456`).
    Anything else (another country, too short or long, letters, empty, None) is None.
    """
    raise NotImplementedError


def same_phone(a: str | None, b: str | None) -> bool:
    """True if both are valid and are the same number. Two invalid numbers are NOT the same."""
    raise NotImplementedError
