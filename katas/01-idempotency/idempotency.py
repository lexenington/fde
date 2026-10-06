"""Kata 1: an idempotency store.

Clients retry. Webhooks arrive twice. Patients send "yes" three times. The rule in every case is the same:
the same key must cause the same effect once. Fill in IdempotencyStore so that tests pass.
"""

import time
from typing import Callable, TypeVar

T = TypeVar("T")


class IdempotencyStore:
    def __init__(self, ttl_seconds: float = 3600, clock: Callable[[], float] = time.time):
        """`clock` returns the current time in seconds. Tests replace it, so use it instead of time.time()."""
        raise NotImplementedError

    def run(self, key: str, fn: Callable[[], T]) -> T:
        """Run `fn` at most once per `key` and return its result. Later calls with the same key return the same
        result without calling `fn` again."""
        raise NotImplementedError
