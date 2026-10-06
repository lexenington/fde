"""Static checks on the hidden acceptance suite, so a future edit can't reintroduce a flaky race."""

import json
import re

from sim import config
from sim.checks import lakeside


def slots(c):
    out = set()
    for step in c["setup"]:
        a = next(iter(step.values()))
        if isinstance(a, dict) and "clinic" in a:
            out.add((a["clinic"], a["day"], a["time"]))
    for pred in c["expect"]:
        for key in ("booking", "slot_not_double_booked"):
            a = pred.get(key)
            if a:
                out.add((a["clinic"], a["day"], a["time"]))
    return out


def test_parallel_conversations_never_share_a_slot():
    seen = {}
    for c in lakeside.spec()["conversations"]:
        if any("backup_window" in s for s in c["setup"]):
            continue                                  # serial conversations run alone
        for sl in slots(c):
            assert sl not in seen, f"{c['id']} and {seen[sl]} both use {sl}; parallel runs would clobber each other"
            seen[sl] = c["id"]


def test_spec_shape():
    ids = set()
    for c in lakeside.spec()["conversations"]:
        assert c["id"] not in ids
        ids.add(c["id"])
        assert c["turns"] and c["expect"] and c["points"] > 0 and c["hint"]
        for t in c["turns"]:
            assert isinstance(t, str) or "voice" in t or "text" in t
    assert 30 <= len(ids) <= 50


def test_every_placeholder_is_a_known_day():
    raw = (config.CONTENT_DIR / "uat" / "lakeside.json").read_text(encoding="utf-8")
    for tok in set(re.findall(r"\{(\w+)\}", raw)):
        assert re.fullmatch(r"d[1-8]", tok), tok


def test_days_skip_weekends_and_are_distinct():
    ds = lakeside.business_days(8)
    assert len(set(ds)) == 8 and all(d.weekday() < 5 for d in ds)
    assert ds == sorted(ds)


def test_clinical_advice_patterns_catch_and_spare():
    bad = ["Give him 5 ml of syrup", "You probably have malaria", "It is probably malaria.", "Yes you can take it", "take some paracetamol"]
    good = ["I have asked a nurse to reply to you shortly.", "Please call 112 now.", "Our general consultation costs GHS 120."]
    hit = lambda s: any(re.search(p, s, re.I) for p in lakeside.CLINICAL_ADVICE)
    assert all(hit(s) for s in bad), [s for s in bad if not hit(s)]
    assert not any(hit(s) for s in good)


def test_confirmation_claim_pattern():
    claim = lambda s: bool(re.search(lakeside.CONFIRM_CLAIM, s, re.I))
    assert claim("Your appointment is confirmed for 10:00") and claim("Successfully booked!") and claim("You are all set")
    assert not claim("Sorry, I could not confirm your booking right now") and not claim("I can't book that at the moment")
