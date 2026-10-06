"""Kata 3: retry with backoff and jitter.

Retry what is worth retrying, as politely as the server asks, and no more.
"""

import random
import time


class HttpError(Exception):
    def __init__(self, status: int, retry_after: float | None = None):
        super().__init__(f"HTTP {status}")
        self.status = status
        self.retry_after = retry_after       # seconds, from a Retry-After header


def retry(fn, *, attempts: int = 5, base: float = 0.5, cap: float = 30.0, sleep=time.sleep, rand=random.random):
    """Call `fn()` and return its result, retrying failures that are worth retrying.

    Worth retrying: HttpError with status 408, 429 or any 5xx, and ConnectionError / TimeoutError.
    Anything else (a 400, a 404, a ValueError...) is raised immediately.

    `attempts` is the total number of calls, including the first. After a retryable failure, wait (using `sleep`)
    `rand() * min(cap, base * 2 ** n)` seconds, where n is 0 for the first retry, 1 for the second, and so on.
    If the error carries `retry_after`, wait at least that long instead if it is longer.
    If the last attempt fails, raise its error (and do not sleep after it).
    """
    raise NotImplementedError
