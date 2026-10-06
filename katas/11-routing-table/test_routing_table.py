import pytest

from routing_table import pick_threshold, routing_table

# 10 documents. confidence, correct, must_review
DOCS = [
    (0.99, True, False), (0.97, True, False), (0.95, True, False), (0.92, True, False), (0.90, False, False),
    (0.85, True, False), (0.80, False, True), (0.70, True, False), (0.60, False, False), (0.40, False, True),
]
RESULTS = [{"confidence": c, "correct": ok, "must_review": mr} for c, ok, mr in DOCS]


def row(t):
    return next(r for r in routing_table(RESULTS, [t]))


def test_everything_automatic_at_threshold_zero():
    r = row(0.0)
    assert (r["auto"], r["review"], r["auto_pct"], r["error_pct"], r["leaked"]) == (10, 0, 100.0, 40.0, 2)


def test_a_middle_threshold():
    r = row(0.9)               # 0.99 0.97 0.95 0.92 0.90 are automatic: one wrong
    assert (r["auto"], r["review"], r["auto_pct"], r["error_pct"], r["leaked"]) == (5, 5, 50.0, 20.0, 0)


def test_the_threshold_is_inclusive():
    assert row(0.92)["auto"] == 4 and row(0.9201)["auto"] == 3


def test_a_high_threshold_automates_nothing():
    r = row(1.0)
    assert (r["auto"], r["review"], r["auto_pct"], r["error_pct"], r["leaked"]) == (0, 10, 0.0, 0.0, 0)


def test_leaks_count_must_review_documents_that_slipped_through():
    assert row(0.8)["leaked"] == 1 and row(0.4)["leaked"] == 2 and row(0.81)["leaked"] == 0


def test_percentages_round_to_one_decimal():
    r = routing_table([{"confidence": 0.9, "correct": i != 0, "must_review": False} for i in range(3)], [0.5])[0]
    assert r["error_pct"] == 33.3 and r["auto_pct"] == 100.0


def test_rows_come_back_in_the_order_asked():
    assert [r["threshold"] for r in routing_table(RESULTS, [0.9, 0.5, 0.99])] == [0.9, 0.5, 0.99]


def test_no_results_gives_zeros_not_a_crash():
    r = routing_table([], [0.5])[0]
    assert (r["auto"], r["review"], r["auto_pct"], r["error_pct"], r["leaked"]) == (0, 0, 0.0, 0.0, 0)


def test_picking_the_lowest_safe_threshold():
    table = routing_table(RESULTS, [0.0, 0.4, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0])
    # 0.85 sends 6 documents through with 1 wrong (16.7%) and leaks nothing; 0.8 would leak a must-review document
    assert pick_threshold(table, max_error_pct=20.0) == 0.85
    assert pick_threshold(table, max_error_pct=0.0) == 0.95


def test_a_leaked_must_review_document_disqualifies_a_threshold_unless_you_allow_it():
    table = routing_table(RESULTS, [0.4, 0.8, 0.9])
    assert pick_threshold(table, max_error_pct=100.0) == 0.9            # 0.4 and 0.8 leak
    assert pick_threshold(table, max_error_pct=100.0, max_leaked=1) == 0.8


def test_none_when_nothing_qualifies():
    table = routing_table(RESULTS, [0.0, 0.5])
    assert pick_threshold(table, max_error_pct=1.0) is None
