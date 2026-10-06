# Kata 3: retry with backoff and jitter

**Time-box: 40 minutes.** Used in: 02/02 (CRM calls, 429 handling), every integration you'll ever write.

**The task.** Implement `retry` in `retry_backoff.py`. `python -m pytest -q katas/03-retry-backoff`.

**What matters**
- *What* to retry is a decision: 408, 429 and 5xx yes; a 400 or a bug, never. Retrying a 400 forever is how a customer's API key gets blocked.
- *How long* to wait: exponential growth, capped, with jitter so a hundred clients don't all come back at the same instant. The server's `Retry-After` is a minimum.
- Say when you give up, and don't sleep after the last attempt.
- `sleep` and `rand` are parameters so the tests are instant and exact. Do the same in your real code.

**Then.** Where does a retry become dangerous? (Hint: a retried POST that already half-worked. Kata 1 is the other half of this.)
