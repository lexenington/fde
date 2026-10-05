"""Run the golden set through extract(), score it, save the run, and diff against the previous run.

Usage:
    python eval.py                 # full run
    python eval.py --only inv_07   # one doc, prints the raw output
"""

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

from extract import MODEL, extract

HERE = Path(__file__).parent
DOCS = HERE / "data" / "docs"
GOLD = json.loads((HERE / "data" / "gold.json").read_text(encoding="utf-8"))
RUNS = HERE / "runs"

# $ per million tokens for claude-opus-5-5; update if you change MODEL
PRICE_IN, PRICE_OUT = 4.00, 20.00
FIELDS = ["is_invoice", "supplier_name", "invoice_number", "invoice_date", "currency", "subtotal", "tax_total", "total"]


def norm_str(s):
    return " ".join(str(s).lower().replace(",", " ").replace(".", " ").split()) if s is not None else None


def field_ok(name, got, want):
    if isinstance(want, list):  # any-of: ambiguity documented in the gold set
        return any(field_ok(name, got, w) for w in want)
    if want is None or got is None:
        return want is None and got is None
    if name in ("subtotal", "tax_total", "total"):
        return abs(float(got) - float(want)) < 0.01
    if name == "currency":
        return str(got).upper() == str(want).upper()
    return norm_str(got) == norm_str(want)


def run_one(doc_id):
    text = (DOCS / f"{doc_id}.txt").read_text(encoding="utf-8")
    try:
        inv, tel = extract(text)
    except anthropic.APIError as e:
        return {"doc": doc_id, "error": f"{type(e).__name__}: {e}"}
    if inv is None:
        return {"doc": doc_id, "error": f"no output (stop_reason={tel['stop_reason']})", **tel}

    gold = GOLD[doc_id]
    got = inv.model_dump()
    fields = FIELDS if gold["expected"].get("is_invoice", True) else ["is_invoice"]
    scores = {f: field_ok(f, got.get(f), gold["expected"].get(f)) for f in fields}
    return {
        "doc": doc_id,
        "output": got,
        "fields": scores,
        "all_fields_ok": all(scores.values()),
        "must_review": gold["must_review"],
        "flagged": inv.needs_review,
        "confidence": inv.confidence,
        **tel,
    }


def threshold_table(results, thresholds=(0.0, 0.5, 0.7, 0.8, 0.9, 0.95)):
    """Routing rule: auto-process if not flagged AND confidence >= t. This table is what the CFO decides on."""
    ok = [r for r in results if "error" not in r]
    rows = []
    for t in thresholds:
        auto = [r for r in ok if not r["flagged"] and r["confidence"] >= t]
        rows.append({
            "threshold": t,
            "auto_pct": round(len(auto) / len(ok), 3) if ok else 0,
            "error_rate_on_auto": round(sum(not r["all_fields_ok"] for r in auto) / len(auto), 3) if auto else None,
            "missed_must_review": sum(r["must_review"] for r in auto),
        })
    return rows


def summarise(results):
    ok = [r for r in results if "error" not in r]
    per_field = {}
    for f in FIELDS:
        vals = [r["fields"][f] for r in ok if f in r["fields"]]
        if vals:
            per_field[f] = round(sum(vals) / len(vals), 3)

    must = [r for r in ok if r["must_review"]]
    clean = [r for r in ok if not r["must_review"]]
    auto = [r for r in ok if not r["flagged"]]
    lat = [r["latency_s"] for r in ok]
    tok_in = sum(r["input_tokens"] for r in ok)
    tok_out = sum(r["output_tokens"] for r in ok)
    cost = tok_in / 1e6 * PRICE_IN + tok_out / 1e6 * PRICE_OUT

    return {
        "docs": len(results),
        "errors": len(results) - len(ok),
        "doc_accuracy": round(sum(r["all_fields_ok"] for r in ok) / len(ok), 3) if ok else 0,
        "field_accuracy": per_field,
        "review_recall": round(sum(r["flagged"] for r in must) / len(must), 3) if must else None,
        "false_flag_rate": round(sum(r["flagged"] for r in clean) / len(clean), 3) if clean else None,
        "auto_processed_pct": round(len(auto) / len(ok), 3) if ok else 0,
        "error_rate_on_auto": round(sum(not r["all_fields_ok"] for r in auto) / len(auto), 3) if auto else None,
        "latency_p50_s": round(statistics.median(lat), 2) if lat else None,
        "latency_max_s": max(lat) if lat else None,
        "cost_usd": round(cost, 4),
        "cost_per_1000_docs_usd": round(cost / len(ok) * 1000, 2) if ok else None,
    }


def print_report(summary, results, previous):
    print(f"\nmodel: {MODEL}")
    for k, v in summary.items():
        prev = previous["summary"].get(k) if previous else None
        delta = ""
        if isinstance(v, (int, float)) and isinstance(prev, (int, float)) and v != prev:
            delta = f"   (was {prev})"
        print(f"  {k:24} {v}{delta}")

    print("\nfailures:")
    for r in results:
        if "error" in r:
            print(f"  {r['doc']}: ERROR {r['error']}")
            continue
        bad = [f for f, ok in r["fields"].items() if not ok]
        review_miss = r["must_review"] and not r["flagged"]
        if bad or review_miss:
            parts = [f"{f}: got {r['output'].get(f)!r} want {GOLD[r['doc']]['expected'].get(f)!r}" for f in bad]
            if review_miss:
                parts.append(f"NOT FLAGGED (should be: {GOLD[r['doc']].get('why')})")
            print(f"  {r['doc']}: " + "; ".join(parts))

    print("\nreview routing (auto = not flagged and confidence >= threshold):")
    print(f"  {'threshold':>9}  {'auto %':>7}  {'err on auto':>11}  {'must-review leaked':>18}")
    for row in threshold_table(results):
        err = "-" if row["error_rate_on_auto"] is None else f"{row['error_rate_on_auto']:.1%}"
        print(f"  {row['threshold']:>9}  {row['auto_pct']:>7.0%}  {err:>11}  {row['missed_must_review']:>18}")

    if previous:
        prev_ok ={r["doc"]: r.get("all_fields_ok") for r in previous["results"]}
        regressions = [r["doc"] for r in results if prev_ok.get(r["doc"]) and not r.get("all_fields_ok")]
        if regressions:
            print(f"\nREGRESSIONS vs last run: {regressions}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="run a single doc id")
    args = ap.parse_args()

    if args.only:
        print(json.dumps(run_one(args.only), indent=2))
        return

    doc_ids = sorted(GOLD)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run_one, doc_ids))
    summary = summarise(results)

    RUNS.mkdir(exist_ok=True)
    prior = sorted(RUNS.glob("*.json"))
    previous = json.loads(prior[-1].read_text()) if prior else None
    out = RUNS / f"{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1000:03d}.json"
    out.write_text(json.dumps({"model": MODEL, "summary": summary, "results": results}, indent=2))

    print_report(summary, results, previous)
    print(f"\nsaved {out.relative_to(HERE)}")


if __name__ == "__main__":
    main()
