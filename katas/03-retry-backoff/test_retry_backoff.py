import pytest

from retry_backoff import HttpError, retry


class Script:
    """A function that raises or returns what it is told, in order."""
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        out = self.outcomes.pop(0)
        if isinstance(out, BaseException):
            raise out
        return out


def run(fn, **kw):
    delays = []
    kw.setdefault("rand", lambda: 1.0)
    result = retry(fn, sleep=delays.append, **kw)
    return result, delays


def test_success_on_the_first_try_never_sleeps():
    fn = Script("ok")
    assert run(fn) == ("ok", [])
    assert fn.calls == 1


def test_backoff_doubles_and_returns_the_eventual_result():
    fn = Script(HttpError(503), HttpError(500), "ok")
    result, delays = run(fn, base=0.5)
    assert result == "ok" and fn.calls == 3
    assert delays == [0.5, 1.0]


def test_jitter_scales_the_delay():
    fn = Script(HttpError(503), HttpError(503), "ok")
    _, delays = run(fn, base=1.0, rand=lambda: 0.25)
    assert delays == [0.25, 0.5]


def test_delay_is_capped():
    fn = Script(*[HttpError(503)] * 5, "ok")
    _, delays = run(fn, attempts=6, base=10, cap=30)
    assert delays == [10, 20, 30, 30, 30]


def test_retry_after_wins_when_it_is_longer():
    fn = Script(HttpError(429, retry_after=7), HttpError(429, retry_after=0.1), "ok")
    _, delays = run(fn, base=0.5)
    assert delays == [7, 1.0]          # 7 > 0.5 jitter; then max(1.0, 0.1)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 422])
def test_client_errors_are_not_retried(status):
    fn = Script(HttpError(status), "never")
    with pytest.raises(HttpError):
        run(fn)
    assert fn.calls == 1


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_these_statuses_are_retried(status):
    fn = Script(HttpError(status), "ok")
    assert run(fn)[0] == "ok"


@pytest.mark.parametrize("exc", [ConnectionError("reset"), TimeoutError("slow")])
def test_network_errors_are_retried(exc):
    assert run(Script(exc, "ok"))[0] == "ok"


def test_other_exceptions_are_raised_straight_away():
    fn = Script(ValueError("bug"), "never")
    with pytest.raises(ValueError):
        run(fn)
    assert fn.calls == 1


def test_giving_up_raises_the_last_error_and_sleeps_one_fewer_time():
    fn = Script(HttpError(500), HttpError(502), HttpError(503))
    delays = []
    with pytest.raises(HttpError) as e:
        retry(fn, attempts=3, sleep=delays.append, rand=lambda: 1.0)
    assert e.value.status == 503 and fn.calls == 3 and len(delays) == 2
