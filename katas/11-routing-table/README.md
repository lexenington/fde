# Kata 11: the routing table

**Time-box: 30 minutes.** Used in: 02/03 (the table you put in front of the CFO), any "confidence → human review" design.

**The task.** Implement `routing_table` and `pick_threshold` in `routing_table.py`. `python -m pytest -q katas/11-routing-table`.

**Why this is the whole job.** The CFO's condition is "I need to know how often it's wrong, and anything it's unsure about goes to a human." This table is that sentence turned into numbers: for each possible line, how much is automatic, how often the automatic part is wrong, and whether anything that *must* have been reviewed slipped through. Choosing the row is a money decision (the cost of a wrong auto-posted invoice versus the cost of a human review).

**Think about**
- `auto_pct` is a share of *all* documents, `error_pct` a share of the *automatic* ones: different denominators
- is the model's own confidence actually calibrated? This table will show you: a high-confidence error is the expensive one

**Then.** Feed it the `runs/` output from your 02/03 eval. Is your cheapest safe threshold the one you'd have guessed?
