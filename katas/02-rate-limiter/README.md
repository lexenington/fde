# Kata 2: token bucket

**Time-box: 30 minutes.** Used in: 02/02 (the CRM's 5 requests a second), the *quota-cut* inject card.

**The task.** Implement `TokenBucket` in `rate_limiter.py`. `python -m pytest -q katas/02-rate-limiter`.

**Watch for**
- Don't use a background thread to refill. Compute the refill from the elapsed time when asked.
- A failed `try_acquire` must not consume tokens.
- `wait_time` is what you'd pass to `sleep` before retrying.

**Then.** The *quota-cut* card changes the limit to 1 request a second. Which of your numbers would you change, and where does that number come from in production (configuration, or the `Retry-After` the server sends)?
