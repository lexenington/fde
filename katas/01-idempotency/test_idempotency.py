import threading
import time

import pytest

from idempotency import IdempotencyStore


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def counter():
    calls = []

    def fn(value="result"):
        calls.append(1)
        return value
    return calls, fn


def test_same_key_runs_once_and_returns_the_same_result():
    store, (calls, fn) = IdempotencyStore(), counter()
    assert store.run("k1", fn) == "result"
    assert store.run("k1", fn) == "result"
    assert len(calls) == 1


def test_different_keys_are_independent():
    store, (calls, fn) = IdempotencyStore(), counter()
    store.run("a", fn)
    store.run("b", fn)
    assert len(calls) == 2


def test_a_falsy_result_is_still_cached():
    """None, 0 and "" are valid results. 'if key in cache and cache[key]' is the classic bug."""
    store, (calls, _) = IdempotencyStore(), counter()
    for value in (None, 0, "", False):
        calls.clear()
        key = f"k-{value!r}"
        assert store.run(key, lambda v=value: calls.append(1) or v) == value
        assert store.run(key, lambda v=value: calls.append(1) or v) == value
        assert len(calls) == 1, f"{value!r} was recomputed"


def test_a_failure_is_not_cached_so_a_retry_can_succeed():
    store = IdempotencyStore()

    def boom():
        raise ValueError("write failed")
    with pytest.raises(ValueError):
        store.run("k", boom)
    assert store.run("k", lambda: "ok") == "ok"
    assert store.run("k", lambda: "should not run") == "ok"


def test_entries_expire_after_the_ttl():
    clock = Clock()
    store, (calls, fn) = IdempotencyStore(ttl_seconds=60, clock=clock), counter()
    store.run("k", fn)
    clock.now += 59
    store.run("k", fn)
    assert len(calls) == 1
    clock.now += 2          # 61 seconds after the first call
    store.run("k", fn)
    assert len(calls) == 2


def test_concurrent_callers_with_the_same_key_run_the_function_once():
    store = IdempotencyStore()
    calls = []
    start = threading.Barrier(8)

    def slow():
        calls.append(1)
        time.sleep(0.1)
        return "booked"
    results = []

    def worker():
        start.wait()
        results.append(store.run("same", slow))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(calls) == 1, f"the function ran {len(calls)} times"
    assert results == ["booked"] * 8


def test_different_keys_do_not_block_each_other():
    store = IdempotencyStore()
    started = threading.Event()
    release = threading.Event()

    def slow():
        started.set()
        release.wait(timeout=5)
        return "slow"
    t = threading.Thread(target=lambda: store.run("slow-key", slow))
    t.start()
    assert started.wait(timeout=5)
    t0 = time.time()
    assert store.run("other-key", lambda: "fast") == "fast"
    assert time.time() - t0 < 1, "an unrelated key waited for a slow one (one global lock?)"
    release.set()
    t.join()
