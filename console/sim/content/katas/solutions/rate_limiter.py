import time
from typing import Callable


class TokenBucket:
    def __init__(self, rate: float, burst: int, clock: Callable[[], float] = time.monotonic):
        self.rate, self.burst, self.clock = rate, burst, clock
        self.tokens, self.last = float(burst), clock()

    def _refill(self):
        now = self.clock()
        self.tokens = min(self.burst, self.tokens + (now - self.last) * self.rate)
        self.last = now

    def _check(self, n: int):
        if n < 1 or n > self.burst:
            raise ValueError(f"n must be between 1 and {self.burst}")

    def try_acquire(self, n: int = 1) -> bool:
        self._check(n)
        self._refill()
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def wait_time(self, n: int = 1) -> float:
        self._check(n)
        self._refill()
        return max(0.0, (n - self.tokens) / self.rate)
