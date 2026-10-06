import json

import pytest

from sim import config, evalview


def res(doc, ok, conf=0.9, flagged=False, must=False, got_total=100.0):
    return {"doc": doc, "output": {"total": got_total}, "fields": {"total": ok}, "all_fields_ok": ok, "must_review": must,
            "flagged": flagged, "confidence": conf}


@pytest.fixture
def lab():
    d = config.LABS_DIR / "03-ai-engineering" / "lab"
    (d / "data" / "docs").mkdir(parents=True)
    (d / "runs").mkdir()
    (d / "data" / "gold.json").write_text(json.dumps({
        "a": {"must_review": False, "expected": {"total": 100.0}}, "b": {"must_review": True, "expected": {"total": 50.0}, "why": "handwritten"}}))
    (d / "data" / "docs" / "b.txt").write_text("INVOICE total 50")
    return d


def save(lab, name, results, summary):
    (lab / "runs" / f"{name}.json").write_text(json.dumps({"model": "m", "summary": summary, "results": results}))


def test_empty_state(lab):
    assert evalview.list_runs() == [] and evalview.detail("nope") is None


def test_failures_show_the_text_and_why(lab):
    save(lab, "r1", [res("a", True), res("b", False, must=True, got_total=40.0)], {"doc_accuracy": 0.5})
    d = evalview.detail("r1")
    (f,) = d["failures"]
    assert f["doc"] == "b" and f["bad"] == [{"field": "total", "got": 40.0, "want": 50.0}] and f["not_flagged"]
    assert f["why"] == "handwritten" and "INVOICE" in f["text"]


def test_compare_finds_regressions_fixes_and_which_way_each_metric_moved(lab):
    save(lab, "r1", [res("a", True), res("b", False, must=True)], {"doc_accuracy": 0.5, "cost_per_1000_docs_usd": 10.0})
    save(lab, "r2", [res("a", False), res("b", True, must=True, flagged=True)], {"doc_accuracy": 0.5, "cost_per_1000_docs_usd": 12.0, "latency_p50_s": 1})
    d = evalview.detail("r2", compare_to="r1")
    assert d["regressions"] == ["a"] and d["fixed"] == ["b"]
    assert d["deltas"] == {"cost_per_1000_docs_usd": {"was": 10.0, "now": 12.0, "better": False}}


def test_routing_matches_eval_py_and_prices_the_choice(lab):
    rs = [res("a", True, 0.95), res("b", False, 0.6, must=True), res("c", True, 0.9, flagged=True)]
    rows = evalview.routing(rs, thresholds=(0.0, 0.8), wrong_cost=100, review_cost=5)
    assert rows[0]["auto"] == 2 and rows[0]["wrong_on_auto"] == 1 and rows[0]["leaked"] == 1
    assert rows[1]["auto"] == 1 and rows[1]["error_rate_on_auto"] == 0.0
    assert rows[0]["cost_per_doc"] == round((100 + 5) / 3, 2) and rows[1]["cost_per_doc"] == round(10 / 3, 2)


def test_run_ids_cannot_escape_the_runs_folder(lab):
    (lab / "secret.json").write_text("{}")
    assert evalview.detail("../secret") is None
