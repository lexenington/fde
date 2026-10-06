import random
import time


class HttpError(Exception):
    def __init__(self, status: int, retry_after: float | None = None):
        super().__init__(f"HTTP {status}")
        self.status = status
        self.retry_after = retry_after


def _retryable(e: BaseException) -> bool:
    if isinstance(e, HttpError):
        return e.status in (408, 429) or e.status >= 500
    return isinstance(e, (ConnectionError, TimeoutError))


def retry(fn, *, attempts: int = 5, base: float = 0.5, cap: float = 30.0, sleep=time.sleep, rand=random.random):
    for n in range(attempts):
        try:
            return fn()
        except Exception as e:
            if not _retryable(e) or n == attempts - 1:
                raise
            delay = rand() * min(cap, base * 2 ** n)
            ra = getattr(e, "retry_after", None)
            if ra:
                delay = max(delay, ra)
            sleep(delay)
