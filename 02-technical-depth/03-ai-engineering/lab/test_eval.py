"""Tests for the grader itself. If the grader is wrong, every number in your CFO report is wrong.

Run: python -m pytest -q   (no API key needed)
"""

from eval import field_ok, summarise, threshold_table


def test_money_tolerance():
    assert field_ok("total", 12075.004, 12075.0)
    assert not field_ok("total", 12075.5, 12075.0)


def test_strings_ignore_case_and_punctuation():
    assert field_ok("supplier_name", "ACCRA PACKAGING LTD.", "Accra Packaging Ltd")
    assert not field_ok("supplier_name", "Accra Packing Ltd", "Accra Packaging Ltd")


def test_null_handling():
    assert field_ok("invoice_number", None, None)
    assert not field_ok("invoice_number", "X-1", None)
    assert not field_ok("invoice_number", None, "X-1")


def test_any_of_gold():
    assert field_ok("subtotal", None, [None, 4200.0])
    assert field_ok("subtotal", 4200.0, [None, 4200.0])
    assert not field_ok("subtotal", 4000.0, [None, 4200.0])


def _r(doc, ok, must, flagged, conf):
    return {"doc": doc, "all_fields_ok": ok, "must_review": must, "flagged": flagged, "confidence": conf,
            "fields": {"total": ok}, "latency_s": 1.0, "input_tokens": 100, "output_tokens": 10}


RESULTS = [
    _r("a", True, False, False, 0.95),
    _r("b", False, False, False, 0.60),   # wrong but confident-ish: should be caught by a higher threshold
    _r("c", True, True, True, 0.40),
    _r("d", False, True, False, 0.85),    # must-review doc the model failed to flag
]


def test_threshold_table_trades_volume_for_accuracy():
    rows = {r["threshold"]: r for r in threshold_table(RESULTS)}
    assert rows[0.0]["auto_pct"] == 0.75 and rows[0.0]["missed_must_review"] == 1
    assert rows[0.7]["auto_pct"] == 0.5 and rows[0.7]["error_rate_on_auto"] == 0.5
    assert rows[0.9]["auto_pct"] == 0.25 and rows[0.9]["error_rate_on_auto"] == 0.0
    assert rows[0.9]["missed_must_review"] == 0


def test_summary_review_metrics():
    s = summarise(RESULTS)
    assert s["review_recall"] == 0.5        # flagged 1 of 2 must-review docs
    assert s["false_flag_rate"] == 0.0
    assert s["doc_accuracy"] == 0.5
