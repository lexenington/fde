"""Kata 11: the table you show the CFO.

"Anything the model is unsure about goes to a human." Where do you draw the line? The routing table shows what
each possible line would cost and save.
"""


def routing_table(results: list[dict], thresholds: list[float]) -> list[dict]:
    """`results` has one dict per document: `{"confidence": 0.93, "correct": True, "must_review": False}`.
    `correct` says whether the model's extraction was right; `must_review` marks documents a human MUST see
    whatever the model thinks (a poisoned invoice, say).

    For each threshold return a row, in the order given:
      {"threshold": t, "auto": n, "review": m, "auto_pct": ..., "error_pct": ..., "leaked": k}
    where a document is processed automatically if `confidence >= threshold` and sent to a human otherwise;
      auto_pct   share of ALL documents that are automatic, as a percentage rounded to 1 decimal
      error_pct  share of the AUTOMATIC documents that are incorrect, as a percentage rounded to 1 decimal
                 (0.0 if nothing is automatic)
      leaked     automatic documents that were `must_review`
    Empty `results` gives rows of zeros.
    """
    raise NotImplementedError


def pick_threshold(table: list[dict], *, max_error_pct: float, max_leaked: int = 0) -> float | None:
    """The lowest threshold (the most automation) whose `error_pct` is at most `max_error_pct` and whose `leaked`
    is at most `max_leaked`. None if no row qualifies."""
    raise NotImplementedError
