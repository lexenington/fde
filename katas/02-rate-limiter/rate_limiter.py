"""Kata 2: a token bucket.

The CRM allows 5 requests a second with bursts of 10. Respect it on your side before it says 429.
"""

import time
from typing import Callable


class TokenBucket:
    def __init__(self, rate: float, burst: int, clock: Callable[[], float] = time.monotonic):
        """`rate` tokens are added per second, up to `burst`. The bucket starts full. Use `clock()` for the time."""
        raise NotImplementedError

    def try_acquire(self, n: int = 1) -> bool:
        """Take `n` tokens if they are available and return True. Otherwise take nothing and return False.
        Raise ValueError if `n` is more than `burst` (it could never succeed) or less than 1."""
        raise NotImplementedError

    def wait_time(self, n: int = 1) -> float:
        """Seconds until `n` tokens will be available (0.0 if they already are). Same ValueError rule."""
        raise NotImplementedError
