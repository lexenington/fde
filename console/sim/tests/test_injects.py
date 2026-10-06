import hashlib
import hmac
import json

import pytest

from sim import config, injects, llm
from sim.crm import make_event, sign, store

LAB = "integration"


def mac(secret, body, ts):
    return hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()


def test_deck_is_well_formed():
    deck = json.loads((config.CONTENT_DIR / "injects" / "integration.json").read_text())
    ids = [c["id"] for c in deck["cards"]]
    assert len(ids) == len(set(ids)) == 6
    for c in deck["cards"]:
        assert c["deliverable"]["prompt"] and len(c["deliverable"]["rubric"]) >= 4
        if c["id"] in ("deadline-moved", "questionnaire"):
            assert c["action"] is None and c["effect"] is None      # pure writing exercises
        else:
            assert c["action"] and c["symptom"]
        if c["action"]:
            assert c["action"]["id"] in injects.ACTIONS
        if c["effect"]:
            assert c["effect"]["type"] in ("tighten_rate", "rotate_secret", "idp_full_path")


def test_draw_never_repeats_and_persists(monkeypatch):
    monkeypatch.setattr(injects, "set_groups_full_path", lambda v: None)
    seen = [injects.draw(LAB, card_id=cid)["id"] for cid in ("deadline-moved", "questionnaire")]
    assert seen == ["deadline-moved", "questionnaire"]
    state = json.loads((injects._dir(LAB) / "drawn.json").read_text())
    assert [d["id"] for d in state["drawn"]] == seen
    assert (injects._dir(LAB) / "01-deadline-moved.md").exists()
    with pytest.raises(injects.InjectError):
        injects.draw(LAB, card_id="deadline-moved")
    for _ in range(4):
        injects.draw(LAB)
    assert injects.view(LAB)["remaining"] == 0
    with pytest.raises(injects.InjectError, match="deck is empty"):
        injects.draw(LAB)


def test_public_view_hides_effects_and_rubrics():
    card = injects.draw(LAB, card_id="quota-cut")
    assert not {"rubric", "effect", "symptom", "deliverable"} & set(card)
    assert "tighten_rate" not in json.dumps(card)
    assert card["hint"] is None and card["has_hint"]
    assert injects.hint(LAB, "quota-cut")["hint"]


def test_quota_cut_changes_the_crm_and_clear_restores_it():
    injects.draw(LAB, card_id="quota-cut")
    assert store.conditions["rate_per_sec"] == 1 and store.conditions["burst"] == 2
    store.reset_tokens()
    assert [store.take_token() for _ in range(3)] == [True, True, False]
    assert injects.conditions()["active"]
    injects.clear_conditions()
    assert store.conditions["rate_per_sec"] == config.RATE_LIMIT_PER_SEC and not injects.conditions()["active"]


def test_conditions_survive_a_crm_wipe():
    injects.draw(LAB, card_id="quota-cut")
    store.reset()
    assert store.conditions["rate_per_sec"] == 1


def test_secret_rotation_signatures():
    card = injects.draw(LAB, card_id="secret-rotation")
    new = store.conditions["webhook_secret_new"]
    assert new and new in card["body"] and "{{new_secret}}" not in card["body"]
    body, ts = b'{"id":"evt_1"}', 1700000000
    old = config.CRM_WEBHOOK_SECRET
    assert sign(body, ts) == f"t={ts},v1={mac(new, body, ts)},v1={mac(old, body, ts)}"      # overlap: both
    store.conditions["webhook_secret_mode"] = "new_only"
    assert sign(body, ts) == f"t={ts},v1={mac(new, body, ts)}"
    assert sign(body, ts, secret=old) == f"t={ts},v1={mac(old, body, ts)}"                  # explicit secret still works
    injects.clear_conditions()
    assert sign(body, ts) == f"t={ts},v1={mac(old, body, ts)}"


def test_claims_change_calls_the_idp(monkeypatch):
    calls = []
    monkeypatch.setattr(injects, "set_groups_full_path", lambda v: calls.append(v))
    injects.draw(LAB, card_id="claims-change")
    assert calls == [True] and store.conditions["idp_full_path"]
    injects.clear_conditions()
    assert calls == [True, False] and not store.conditions["idp_full_path"]


def test_idp_failure_is_reported_not_crashed(monkeypatch):
    def boom(v):
        raise injects.IdPAdminError("Keycloak unreachable")
    monkeypatch.setattr(injects, "set_groups_full_path", boom)
    with pytest.raises(injects.InjectError, match="Keycloak unreachable"):
        injects.draw(LAB, card_id="claims-change")
    assert injects.view(LAB)["drawn"] == []      # a card whose effect failed is not consumed


def test_reply_gets_feedback_and_is_saved():
    injects.draw(LAB, card_id="deadline-moved")
    seen = {}

    def backend(model, system, messages, schema, max_tokens):
        seen["user"] = messages[0]["content"]
        return injects.Feedback(rating=9, what_works=["a", "b", "c"], fix_next=["1", "2", "3", "4"], sharper_sentence="Yes, and X moves.")
    llm.set_backend(backend)
    out = injects.respond(LAB, "deadline-moved", "Yes, we can do SSO and the CRM sync by Thursday; SCIM moves to phase 2.")
    assert out["feedback"]["rating"] == 5 and len(out["feedback"]["what_works"]) == 2 and len(out["feedback"]["fix_next"]) == 3
    assert "Rubric:" in seen["user"] and "<reply>" in seen["user"]
    md = (injects._dir(LAB) / "01-deadline-moved.md").read_text()
    assert "Your reply" in md and "Feedback (5/5)" in md


def test_reply_is_kept_even_if_feedback_fails():
    injects.draw(LAB, card_id="deadline-moved")

    def boom(*a, **k):
        raise llm.LLMUnavailable("down")
    llm.set_backend(boom)
    with pytest.raises(llm.LLMUnavailable):
        injects.respond(LAB, "deadline-moved", "A real reply that is long enough to count as one.")
    assert injects.view(LAB)["drawn"][0]["response"].startswith("A real reply")


def test_reply_validation():
    injects.draw(LAB, card_id="deadline-moved")
    with pytest.raises(injects.InjectError):
        injects.respond(LAB, "deadline-moved", "ok")
    with pytest.raises(injects.InjectError):
        injects.respond(LAB, "questionnaire", "A real reply that is long enough to count as one.")   # not drawn


def test_cards_without_a_check_say_so():
    injects.draw(LAB, card_id="questionnaire")
    with pytest.raises(injects.InjectError, match="no check"):
        injects.run_action(LAB, "questionnaire")


def test_make_event_accepts_a_timestamp():
    e = make_event("deal.stage_changed", {"deal_id": "d", "stage": "won"}, occurred_at="2026-01-01T00:00:00+00:00")
    assert e["occurred_at"] == "2026-01-01T00:00:00+00:00"
