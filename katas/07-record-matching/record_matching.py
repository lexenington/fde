"""Kata 7: clusters from pairs, and a score for them.

Matching says "A looks like B" and "B looks like C". Clustering turns those pairs into customers. Scoring tells
the customer how often you're wrong.
"""

from typing import Iterable


def cluster(pairs: Iterable[tuple[str, str]], ids: Iterable[str]) -> list[set[str]]:
    """Group ids into clusters: two ids are in the same cluster if they are linked by a chain of pairs
    (A-B and B-C puts A, B and C together). Every id in `ids` appears in exactly one cluster, alone if it has no
    pairs. Ids that appear only in `pairs` are included too. Must handle hundreds of thousands of pairs quickly
    (no recursion)."""
    raise NotImplementedError


def pairwise_f1(predicted: list[set[str]], truth: list[set[str]]) -> tuple[float, float, float]:
    """Score `predicted` clusters against `truth` clusters, returning (precision, recall, f1).

    Count *pairs*: a cluster {a,b,c} contains the pairs ab, ac, bc. Precision is the share of predicted pairs that
    are also true pairs; recall is the share of true pairs that were predicted. If there are no predicted pairs,
    precision is 1.0; if there are no true pairs, recall is 1.0. f1 is 0.0 when precision + recall is 0.
    """
    raise NotImplementedError
