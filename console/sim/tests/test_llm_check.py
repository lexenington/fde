import pytest

from sim import injects, llm, llm_check, stakeholders as sh


def backend(model, system, messages, schema, max_tokens):
    if schema is sh.Turn:
        return sh.Turn(reply="It happened last Tuesday.", revealed_fact_ids=[])
    if schema is sh.Debrief:
        return sh.Debrief(dimensions=[sh.DimScore(name=n, score=4, evidence="e", advice="a") for n, _ in sh.DIMENSIONS],
                          verdict="Good.", missed=[], next_time=["a", "b", "c"])
    return injects.Feedback(rating=4, what_works=["clear"], fix_next=["name a date"], sharper_sentence="We will confirm by 5pm today.")


def test_the_smoke_check_passes_against_a_well_behaved_model(capsys):
    llm.set_backend(backend)
    assert llm_check.run() is True
    assert capsys.readouterr().out.count("PASS") == 3


def test_it_says_so_when_there_is_no_key(capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm_check.run() is False and "ANTHROPIC_API_KEY" in capsys.readouterr().out


def test_a_malformed_debrief_is_reported_as_a_failure_not_a_crash(capsys):
    def bad(model, system, messages, schema, max_tokens):
        if schema is sh.Debrief:
            return sh.Debrief(dimensions=[], verdict="", missed=[], next_time=[])
        return backend(model, system, messages, schema, max_tokens)
    llm.set_backend(bad)
    assert llm_check.run() is False
    out = capsys.readouterr().out
    assert "expected 6 scored dimensions" in out and "FAIL" in out


def test_it_leaves_the_configured_folders_as_it_found_them():
    from sim import config
    llm.set_backend(backend)
    before = (config.PRACTICE_DIR, config.LABS_DIR)
    llm_check.run()
    assert (config.PRACTICE_DIR, config.LABS_DIR) == before
