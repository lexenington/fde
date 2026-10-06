"""Lab 02/03 viewer: reads the runs that `python eval.py` saves and makes them easy to compare.

The simulator never calls Claude here and needs no key: you run eval.py on your machine (your key, your spend), and
the Console shows the metric history, what changed between two runs, every failing document next to its text and
gold answer, and the review-routing table recomputed with a cost model you can edit.
"""

import json

from . import config

LAB = "03-ai-engineering"
HEADLINE = ["doc_accuracy", "review_recall", "false_flag_rate", "auto_processed_pct", "error_rate_on_auto", "latency_p50_s", "cost_per_1000_docs_usd"]
# Higher is better for these; the rest are better when lower
HIGHER_BETTER = {"doc_accuracy", "review_recall", "auto_processed_pct"}


def lab_dir():
    return config.LABS_DIR / LAB / "lab"


def _gold():
    p = lab_dir() / "data" / "gold.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def list_runs():
    d = lab_dir() / "runs"
    out = []
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        out.append({"id": p.stem, "model": r.get("model"), "summary": r.get("summary", {})})
    return out


def _load(run_id):
    p = lab_dir() / "runs" / f"{run_id}.json"
    if "/" in run_id or "\\" in run_id or not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def routing(results, thresholds=(0.0, 0.5, 0.7, 0.8, 0.9, 0.95), wrong_cost=None, review_cost=None):
    """Same rule as eval.py: auto = not flagged and confidence >= t. Optionally price it in one currency."""
    ok = [r for r in results if "error" not in r]
    rows = []
    for t in thresholds:
        auto = [r for r in ok if not r["flagged"] and r["confidence"] >= t]
        wrong = sum(not r["all_fields_ok"] for r in auto)
        row = {"threshold": t, "auto": len(auto), "auto_pct": round(len(auto) / len(ok), 3) if ok else 0,
               "wrong_on_auto": wrong, "error_rate_on_auto": round(wrong / len(auto), 3) if auto else None,
               "leaked": sum(r["must_review"] for r in auto)}
        if wrong_cost is not None and review_cost is not None and ok:
            row["cost_per_doc"] = round((wrong * wrong_cost + (len(ok) - len(auto)) * review_cost) / len(ok), 2)
        rows.append(row)
    return rows


def detail(run_id, compare_to=None, wrong_cost=None, review_cost=None):
    run = _load(run_id)
    if run is None:
        return None
    gold, docs = _gold(), lab_dir() / "data" / "docs"
    prev = _load(compare_to) if compare_to else None
    prev_ok = {r["doc"]: r.get("all_fields_ok") for r in prev["results"]} if prev else {}
    failures, regressions, fixed = [], [], []
    for r in run["results"]:
        doc, g = r["doc"], gold.get(r["doc"], {})
        if "error" in r:
            failures.append({"doc": doc, "error": r["error"]})
            continue
        bad = [{"field": f, "got": r["output"].get(f), "want": g.get("expected", {}).get(f)} for f, ok in r["fields"].items() if not ok]
        missed_review = r["must_review"] and not r["flagged"]
        if bad or missed_review:
            p = docs / f"{doc}.txt"
            failures.append({"doc": doc, "bad": bad, "not_flagged": missed_review, "why": g.get("why"), "confidence": r["confidence"],
                             "text": p.read_text(encoding="utf-8")[:2500] if p.exists() else None})
        if prev:
            if prev_ok.get(doc) and not r.get("all_fields_ok"):
                regressions.append(doc)
            if prev_ok.get(doc) is False and r.get("all_fields_ok"):
                fixed.append(doc)
    deltas = {}
    if prev:
        for k in HEADLINE:
            a, b = run["summary"].get(k), prev["summary"].get(k)
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a != b:
                better = (a > b) == (k in HIGHER_BETTER)
                deltas[k] = {"was": b, "now": a, "better": better}
    return {"id": run_id, "model": run.get("model"), "summary": run["summary"], "failures": failures, "compare_to": compare_to,
            "deltas": deltas, "regressions": regressions, "fixed": fixed,
            "routing": routing(run["results"], wrong_cost=wrong_cost, review_cost=review_cost)}
