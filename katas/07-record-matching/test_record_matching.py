import time

import pytest

from record_matching import cluster, pairwise_f1


def as_set(clusters):
    return {frozenset(c) for c in clusters}


def test_a_chain_of_pairs_is_one_cluster():
    got = cluster([("a", "b"), ("b", "c")], ["a", "b", "c"])
    assert as_set(got) == {frozenset("abc")}


def test_separate_groups_stay_separate_and_singletons_survive():
    got = cluster([("a", "b"), ("x", "y")], ["a", "b", "c", "x", "y"])
    assert as_set(got) == {frozenset("ab"), frozenset("c"), frozenset("xy")}


def test_ids_that_only_appear_in_pairs_are_included():
    assert as_set(cluster([("a", "z")], ["a"])) == {frozenset("az")}


def test_order_and_duplicates_do_not_matter():
    pairs = [("c", "d"), ("a", "b"), ("b", "c"), ("a", "b"), ("d", "c")]
    assert as_set(cluster(pairs, "abcd")) == {frozenset("abcd")}


def test_every_id_is_in_exactly_one_cluster():
    got = cluster([("a", "b"), ("b", "c"), ("d", "e")], list("abcdef"))
    members = [m for c in got for m in c]
    assert sorted(members) == list("abcdef") and len(members) == len(set(members))


def test_a_long_chain_does_not_blow_the_stack_or_the_clock():
    n = 200_000
    ids = [str(i) for i in range(n)]
    pairs = [(str(i), str(i + 1)) for i in range(n - 1)]
    t0 = time.time()
    got = cluster(pairs, ids)
    assert len(got) == 1 and len(got[0]) == n
    assert time.time() - t0 < 3, "too slow: use union-find with path compression"


def test_a_perfect_prediction_scores_one():
    truth = [{"a", "b", "c"}, {"d"}]
    assert pairwise_f1(truth, truth) == (1.0, 1.0, 1.0)


def test_merging_two_customers_costs_precision():
    truth = [{"a", "b"}, {"c", "d"}]
    predicted = [{"a", "b", "c", "d"}]          # 6 predicted pairs, 2 true
    p, r, f = pairwise_f1(predicted, truth)
    assert p == pytest.approx(2 / 6) and r == 1.0 and f == pytest.approx(0.5)


def test_missing_a_merge_costs_recall():
    truth = [{"a", "b", "c"}]
    predicted = [{"a", "b"}, {"c"}]             # 1 predicted pair, 3 true
    p, r, f = pairwise_f1(predicted, truth)
    assert p == 1.0 and r == pytest.approx(1 / 3) and f == pytest.approx(0.5)


def test_empty_edge_cases_follow_the_stated_conventions():
    assert pairwise_f1([{"a"}, {"b"}], [{"a"}, {"b"}]) == (1.0, 1.0, 1.0)
    p, r, f = pairwise_f1([{"a"}, {"b"}], [{"a", "b"}])
    assert (p, r, f) == (1.0, 0.0, 0.0)
    p, r, f = pairwise_f1([{"a", "b"}], [{"a"}, {"b"}])
    assert (p, r, f) == (0.0, 1.0, 0.0)
