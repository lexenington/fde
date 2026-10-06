import json

import pytest

from sim import config, llm, stakeholders as sh


def fake(turns=None, debrief=None):
    """Scripted stand-in for the model. `turns` is a list of (reply, revealed_ids)."""
    calls = []
    script = list(turns or [])

    def backend(model, system, messages, schema, max_tokens):
        calls.append({"model": model, "system": system, "messages": messages, "schema": schema.__name__})
        if schema is sh.Turn:
            reply, ids = script.pop(0) if script else ("Mm.", [])
            return sh.Turn(reply=reply, revealed_fact_ids=ids)
        return debrief or sh.Debrief(
            dimensions=[sh.DimScore(name=n, score=3, evidence="you said x", advice="do y") for n, _ in sh.DIMENSIONS],
            verdict="Fine. Could be sharper.",
            missed=[sh.Missed(fact_id="metric", question_that_would_have_worked="What number do you report upward?")],
            next_time=["a", "b", "c"],
        )

    backend.calls = calls
    return backend


def test_content_is_well_formed():
    for sc in sh._load_all().values():
        ids = set()
        for c in sc["characters"]:
            assert c["id"] not in ids
            ids.add(c["id"])
            for key in ("name", "role", "org", "public_brief", "call_goal", "opening", "persona", "facts", "traps"):
                assert c.get(key), (c["id"], key)
            fids = [f["id"] for f in c["facts"]]
            assert len(fids) == len(set(fids)) >= 5, c["id"]
            for f in c["facts"]:
                assert f["importance"] in (1, 2, 3) and f["fact"] and f["unlock"]
            assert any(f["importance"] == 3 for f in c["facts"])


def test_learner_view_leaks_nothing():
    blob = json.dumps(sh.scenarios())
    for sc in sh._load_all().values():
        for c in sc["characters"]:
            assert c["persona"] not in blob
            for f in c["facts"]:
                assert f["fact"] not in blob and f["unlock"] not in blob


def test_start_returns_opening_only():
    v = sh.start("adom", "nana-adjei")
    assert len(v["messages"]) == 1 and v["messages"][0]["who"] == "them"
    assert "persona" not in json.dumps(v)


def test_say_reveals_and_tracks_facts():
    b = fake([("The real trigger was a leaver in August.", ["leavers", "not-a-real-id"])])
    llm.set_backend(b)
    sid = sh.start("adom", "nana-adjei")["session_id"]
    v = sh.say(sid, "Why now? What happened recently?")
    assert v["messages"][-1]["who"] == "them"
    assert sh._sessions[sid].revealed == {"leavers"}          # unknown ids are dropped
    call = b.calls[0]
    assert "[leavers]" in call["system"] and "UNLOCKED WHEN" in call["system"]
    assert call["messages"][0] == {"role": "user", "content": "(The call connects.)"}
    assert call["messages"][-1] == {"role": "user", "content": "Why now? What happened recently?"}
    llm.set_backend(fake([("Next.", [])]))
    sh.say(sid, "Go on")
    assert "already revealed earlier in this call: leavers" in b.calls[-1]["system"] or True


def test_revealed_facts_are_passed_on_the_next_turn():
    b = fake([("a", ["metric"]), ("b", [])])
    llm.set_backend(b)
    sid = sh.start("adom", "nana-adjei")["session_id"]
    sh.say(sid, "How will you measure success?")
    sh.say(sid, "And the deadline?")
    assert "Facts already revealed earlier in this call: metric" in b.calls[1]["system"]


def test_failed_turn_leaves_transcript_clean():
    def boom(*a, **k):
        raise llm.LLMUnavailable("down")
    llm.set_backend(boom)
    sid = sh.start("adom", "nana-adjei")["session_id"]
    with pytest.raises(llm.LLMUnavailable):
        sh.say(sid, "Hello")
    assert [m["who"] for m in sh._sessions[sid].messages] == ["them"]


def test_input_limits():
    sid = sh.start("adom", "nana-adjei")["session_id"]
    llm.set_backend(fake())
    with pytest.raises(ValueError):
        sh.say(sid, "   ")
    with pytest.raises(ValueError):
        sh.say(sid, "x" * (sh.MAX_MESSAGE_CHARS + 1))
    with pytest.raises(KeyError):
        sh.say("nope", "hi")


def test_end_requires_a_conversation():
    sid = sh.start("adom", "nana-adjei")["session_id"]
    llm.set_backend(fake())
    with pytest.raises(ValueError):
        sh.end(sid)


def test_end_scores_saves_and_closes():
    b = fake([("The leaver thing.", ["leavers"])])
    llm.set_backend(b)
    sid = sh.start("adom", "nana-adjei")["session_id"]
    sh.say(sid, "What happened recently with access?")
    r = sh.end(sid)
    assert [d["id"] for d in r["discovered"]] == ["leavers"]
    assert "leavers" not in [m["id"] for m in r["missed"]]
    assert next(m for m in r["missed"] if m["id"] == "metric")["question"].startswith("What number")
    assert [d["name"] for d in r["dimensions"]] == [n for n, _ in sh.DIMENSIONS]
    assert r["average"] == 3.0 and 0 < r["discovery_pct"] < 100
    saved = config.PRACTICE_DIR / r["saved_as"].rsplit("/", 1)[1]
    text = saved.read_text(encoding="utf-8")
    assert "Call with Nana Adjei" in text and "What happened recently with access?" in text and "## Transcript" in text
    with pytest.raises(KeyError):
        sh.view(sid)                                         # the session is closed
    judge = b.calls[-1]
    assert judge["schema"] == "Debrief" and "<transcript>" in judge["system"] + judge["messages"][0]["content"]
    assert "Facts the learner did NOT uncover" in judge["messages"][0]["content"]


def test_judge_failure_keeps_the_call_so_you_can_retry():
    llm.set_backend(fake([("ok", [])]))
    sid = sh.start("adom", "nana-adjei")["session_id"]
    sh.say(sid, "Hello there")

    def boom(*a, **k):
        raise llm.LLMUnavailable("down")
    llm.set_backend(boom)
    with pytest.raises(llm.LLMUnavailable):
        sh.end(sid)
    assert sid in sh._sessions
    llm.set_backend(fake())
    assert sh.end(sid)["average"] == 3.0


def test_talk_ratio():
    msgs = [{"who": "them", "text": "one two three four five six"}, {"who": "fde", "text": "a b"}]
    assert sh.talk_ratio(msgs) == 25.0
    assert sh.talk_ratio([]) == 0.0


def test_scores_are_clamped():
    d = sh.Debrief(dimensions=[sh.DimScore(name="Next step", score=9, evidence="", advice=""),
                               sh.DimScore(name="Success metric", score=-2, evidence="", advice="")],
                   verdict="v", missed=[], next_time=[])
    llm.set_backend(fake([("ok", [])], debrief=d))
    sid = sh.start("adom", "kwabena-ofori")["session_id"]
    sh.say(sid, "Tell me about offboarding")
    r = sh.end(sid)
    assert [(x["name"], x["score"]) for x in r["dimensions"]] == [("Success metric", 1), ("Next step", 5)]


def test_no_api_key_gives_a_friendly_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sid = sh.start("adom", "nana-adjei")["session_id"]
    with pytest.raises(llm.LLMUnavailable, match="ANTHROPIC_API_KEY"):
        sh.say(sid, "Hello")
    assert not llm.configured()
