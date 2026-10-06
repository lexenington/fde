import threading
import time
from typing import Callable, TypeVar

T = TypeVar("T")
_MISSING = object()


class IdempotencyStore:
    def __init__(self, ttl_seconds: float = 3600, clock: Callable[[], float] = time.time):
        self.ttl, self.clock = ttl_seconds, clock
        self._results: dict[str, tuple[float, object]] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def _lock_for(self, key: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())

    def _cached(self, key: str):
        hit = self._results.get(key)
        if hit and self.clock() - hit[0] < self.ttl:
            return hit[1]
        if hit:
            del self._results[key]
        return _MISSING

    def run(self, key: str, fn: Callable[[], T]) -> T:
        with self._lock_for(key):
            got = self._cached(key)
            if got is not _MISSING:
                return got
            value = fn()                       # an exception propagates and nothing is stored
            self._results[key] = (self.clock(), value)
            return value
