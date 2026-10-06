from datetime import date


def _d(x):
    return x if isinstance(x, date) else date.fromisoformat(x)


def value_as_of(base, history, as_of):
    when = _d(as_of)
    live = [h for h in history if _d(h["effective"]) <= when]
    if not live:
        return base, "base"
    best = max(live, key=lambda h: (_d(h["effective"]), h["circular"]))
    return best["value"], best["circular"]


def upcoming(history, as_of):
    when = _d(as_of)
    return sorted((h for h in history if _d(h["effective"]) > when), key=lambda h: (_d(h["effective"]), h["circular"]))
