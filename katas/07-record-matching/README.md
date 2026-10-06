# Kata 7: clusters from pairs, and a score

**Time-box: 45 minutes.** Used in: 02/01 (the Kumasi Fresh Foods lab's F1 ≥ 0.92), Savanna's three disagreeing sources.

**The task.** Implement `cluster` and `pairwise_f1` in `record_matching.py`. `python -m pytest -q katas/07-record-matching`.

**Think about**
- union-find with path compression, written iteratively. A chain of 200,000 links is a real customer file
- why *pairs*, not clusters: the score treats "merged two customers" and "split one customer" as different errors, which is the conversation you have with the ops manager
- which of the two errors hurts a business more (two customers' balances combined, or one customer listed twice)? That's the REPORT.md question in the lab

**Then.** Use `pairwise_f1` in your 02/01 pipeline instead of reading `check.py`'s number blindly. Does it agree?
