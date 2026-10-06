import pytest

from phone_normalise import normalise_gh_phone, same_phone

GOOD = "+233244123456"


@pytest.mark.parametrize("raw", [
    "0244123456", "+233244123456", "233244123456", "00233244123456", "244123456",
    "024 412 3456", "024-412-3456", "(024) 412 3456", "+233 24 412 3456", "+233-24-412-3456", "024.412.3456",
    "+233 (0) 24 412 3456", "  0244123456  ", "+233 24 412 3456",
])
def test_every_way_people_write_it_becomes_one_number(raw):
    assert normalise_gh_phone(raw) == GOOD


@pytest.mark.parametrize("raw,want", [("0541234567", "+233541234567"), ("+233 55 123 4567", "+233551234567"), ("0201234567", "+233201234567")])
def test_other_prefixes(raw, want):
    assert normalise_gh_phone(raw) == want


@pytest.mark.parametrize("raw", [
    None, "", "   ", "N/A", "none", "0", "024412", "02441234567", "0244123456789",
    "0144123456", "0344123456", "0944123456",                  # nine digits but not a mobile prefix
    "+2348031234567", "+447911123456", "+1 415 555 2671",       # other countries
    "024 412 345a", "phone: ???",
])
def test_anything_else_is_none(raw):
    assert normalise_gh_phone(raw) is None


def test_same_phone():
    assert same_phone("0244123456", "+233 24 412 3456") is True
    assert same_phone("0244123456", "0244123457") is False


def test_two_invalid_numbers_are_not_the_same():
    assert same_phone("N/A", "N/A") is False
    assert same_phone(None, None) is False
    assert same_phone("0244123456", None) is False


def test_is_idempotent():
    once = normalise_gh_phone("024-412-3456")
    assert normalise_gh_phone(once) == once
