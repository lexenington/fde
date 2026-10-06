# Kata 12: five queries every customer's data needs

**Time-box: 45 minutes.** Used in: 02/01 (profiling and reconciling three sources), Lakeside's history table (no-show analysis), Savanna's loans and repayments.

**The task.** Fill in the five SQL strings in `queries.py`. `python -m pytest -q katas/12-sql-analysis`.

**What each one practises**
1. *latest row per group* with `ROW_NUMBER() OVER (PARTITION BY ...)`, including the tie-break
2. *"nobody has done X recently"* with `NOT EXISTS`, and what happens at the boundary
3. a *running total* with a window function, and an ordering that is deterministic when dates tie
4. *finding duplicates* by normalising first, which is the first step of any entity-resolution job
5. an *upsert* that must not overwrite what it shouldn't

**Then.** Run the same ideas against your Lakeside replica: which weekday has the worst no-show rate, and does a reminder (`rem_sent`) change it?
