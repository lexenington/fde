import re


def normalise_gh_phone(raw):
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if re.search(r"[A-Za-z?]", s):
        return None
    plus = s.startswith("+")
    digits = re.sub(r"\D", "", s)
    if plus or digits.startswith("00"):
        digits = digits[2:] if digits.startswith("00") and not plus else digits
        if not digits.startswith("233"):
            return None
        digits = digits[3:]
        digits = digits[1:] if len(digits) == 10 and digits.startswith("0") else digits
    elif digits.startswith("233") and len(digits) == 12:
        digits = digits[3:]
    elif digits.startswith("0") and len(digits) == 10:
        digits = digits[1:]
    if not re.fullmatch(r"[25]\d{8}", digits):
        return None
    return "+233" + digits


def same_phone(a, b):
    na, nb = normalise_gh_phone(a), normalise_gh_phone(b)
    return na is not None and na == nb
