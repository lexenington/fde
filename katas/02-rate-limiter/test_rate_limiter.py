import pytest

from rate_limiter import TokenBucket


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def test_starts_full_then_runs_dry():
    clock = Clock()
    b = TokenBucket(rate=5, burst=10, clock=clock)
    assert [b.try_acquire() for _ in range(10)] == [True] * 10
    assert b.try_acquire() is False


def test_refills_with_time():
    clock = Clock()
    b = TokenBucket(rate=5, burst=10, clock=clock)
    for _ in range(10):
        b.try_acquire()
    clock.now += 0.2                 # one token
    assert b.try_acquire() is True
    assert b.try_acquire() is False


def test_fractional_refill_accumulates():
    clock = Clock()
    b = TokenBucket(rate=1, burst=1, clock=clock)
    assert b.try_acquire() is True
    for _ in range(3):               # three quarter-seconds: still less than one token
        clock.now += 0.25
        assert b.try_acquire() is False
    clock.now += 0.25                # a full second since the token was taken
    assert b.try_acquire() is True


def test_never_holds_more_than_burst():
    clock = Clock()
    b = TokenBucket(rate=5, burst=3, clock=clock)
    clock.now += 3600
    assert [b.try_acquire() for _ in range(4)] == [True, True, True, False]


def test_a_failed_attempt_takes_nothing():
    clock = Clock()
    b = TokenBucket(rate=1, burst=5, clock=clock)
    assert b.try_acquire(4) is True       # 1 left
    assert b.try_acquire(3) is False      # not enough, and it must not consume the 1 that is there
    assert b.try_acquire(1) is True


def test_wait_time_says_when_to_retry():
    clock = Clock()
    b = TokenBucket(rate=2, burst=4, clock=clock)
    assert b.wait_time() == 0.0
    b.try_acquire(4)
    assert b.wait_time(1) == pytest.approx(0.5)
    assert b.wait_time(3) == pytest.approx(1.5)
    clock.now += 0.25
    assert b.wait_time(1) == pytest.approx(0.25)


def test_asking_for_more_than_the_burst_is_a_bug():
    b = TokenBucket(rate=5, burst=10, clock=Clock())
    for call in (b.try_acquire, b.wait_time):
        with pytest.raises(ValueError):
            call(11)
        with pytest.raises(ValueError):
            call(0)
