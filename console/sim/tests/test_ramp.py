import pytest

from sim import ramp


def test_start_requires_a_codebase_and_only_one_active_ramp():
    with pytest.raises(ValueError):
        ramp.start("  ")
    ramp.start("Odoo", now=0)
    with pytest.raises(ValueError, match="already running"):
        ramp.start("ERPNext", now=1)


def test_marks_are_stamped_in_minutes_since_start_and_can_be_undone():
    ramp.start("Odoo", now=1000)
    s = ramp.mark("running", "docker compose, 2 failed attempts", now=1000 + 45 * 60)
    assert s["ramps"][0]["marks"]["running"]["minutes"] == 45.0
    with pytest.raises(ValueError):
        ramp.mark("nonsense")
    assert "running" not in ramp.unmark("running")["ramps"][0]["marks"]


def test_the_skeleton_log_is_built_from_your_stamps_with_time_per_step():
    ramp.start("Odoo", now=0)
    ramp.mark("running", "slow image pull", now=60 * 45)
    ramp.mark("trace", "", now=60 * 100)
    sk = ramp.state(now=60 * 100)["skeleton"]
    assert "| 45 min | Running locally with seed data | 45 min | slow image pull |" in sk
    assert "| 100 min | Traced one real request end to end | 55 min |" in sk and "## Where I lost time" in sk


def test_a_second_finished_ramp_is_compared_with_the_first_and_over_day_is_flagged():
    ramp.start("Odoo", now=0)
    ramp.mark("running", now=3600)
    ramp.finish(now=9 * 3600)
    ramp.start("ERPNext", now=10 ** 6)
    ramp.mark("running", now=10 ** 6 + 1800)
    s = ramp.finish(now=10 ** 6 + 7 * 3600)
    assert s["ramps"][0]["over_day"] and not s["ramps"][1]["over_day"]
    row = s["compare"]["rows"][0]
    assert (row["first"], row["latest"]) == (60.0, 30.0) and s["active"] is None


def test_abandoned_ramps_are_not_compared():
    ramp.start("A", now=0); ramp.finish(abandon=True, now=10)
    ramp.start("B", now=100); ramp.finish(now=200)
    assert ramp.state()["compare"] is None


def test_doc_checks(tmp_path):
    from sim import config
    d = config.LABS_DIR / "05-unfamiliar-territory" / "lab"
    d.mkdir(parents=True)
    (d / "ARCHITECTURE.md").write_text("# Components\nx\n## Request flow\ny\n")
    (d / "DATA-MAP.md").write_text("\n".join(f"- `table_{i}`: rows" for i in range(10)))
    (d / "RAMP-LOG.md").write_text("I lost two hours on Docker.")
    docs = {x["doc"]: x for x in ramp.state()["docs"]}
    assert [c["ok"] for c in docs["ARCHITECTURE.md"]["checks"]] == [True, True, True, False]
    assert docs["DATA-MAP.md"]["checks"][0]["ok"] and not docs["GLOSSARY.md"]["exists"]
    assert [c["ok"] for c in docs["RAMP-LOG.md"]["checks"]] == [True, False]
