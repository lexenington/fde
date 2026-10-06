import hashlib
import hmac

import pytest

from webhook_signature import verify

SECRET = "whsec_test"
BODY = b'{"id":"evt_1","type":"deal.stage_changed"}'
NOW = 1_790_000_000


def mac(secret, body, t):
    return hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()


def header(t=NOW, secret=SECRET, body=BODY, extra=()):
    parts = [f"t={t}", f"v1={mac(secret, body, t)}"] + [f"v1={e}" for e in extra]
    return ",".join(parts)


def test_a_good_signature_passes():
    assert verify(SECRET, header(), BODY, now=NOW) is True


def test_a_wrong_secret_fails():
    assert verify("whsec_other", header(), BODY, now=NOW) is False


def test_a_changed_body_fails():
    assert verify(SECRET, header(), BODY + b" ", now=NOW) is False


def test_the_timestamp_is_part_of_what_is_signed():
    h = header(t=NOW).replace(f"t={NOW}", f"t={NOW + 1}")
    assert verify(SECRET, h, BODY, now=NOW) is False


def test_old_and_future_timestamps_are_rejected():
    assert verify(SECRET, header(t=NOW - 301), BODY, now=NOW) is False
    assert verify(SECRET, header(t=NOW + 301), BODY, now=NOW) is False


def test_the_tolerance_edge_is_inclusive_and_configurable():
    assert verify(SECRET, header(t=NOW - 300), BODY, now=NOW) is True
    assert verify(SECRET, header(t=NOW - 31), BODY, now=NOW, tolerance=30) is False
    assert verify(SECRET, header(t=NOW - 30), BODY, now=NOW, tolerance=30) is True


def test_any_of_several_signatures_may_match():
    """Secret rotation: the provider signs with the new and the old secret. The first one is not ours."""
    h = f"t={NOW},v1={mac('whsec_new', BODY, NOW)},v1={mac(SECRET, BODY, NOW)}"
    assert verify(SECRET, h, BODY, now=NOW) is True
    h2 = f"t={NOW},v1={mac('whsec_x', BODY, NOW)},v1={mac('whsec_y', BODY, NOW)}"
    assert verify(SECRET, h2, BODY, now=NOW) is False


@pytest.mark.parametrize("bad", [
    "", "garbage", "t=,v1=", f"t=abc,v1={mac(SECRET, BODY, NOW)}", f"v1={mac(SECRET, BODY, NOW)}", f"t={NOW}",
    f"t={NOW},v1=not-hex", f"t={NOW},v1=", ",,,", "t=1,t=2,v1=ab",
])
def test_malformed_headers_return_false_and_never_raise(bad):
    assert verify(SECRET, bad, BODY, now=NOW) is False


def test_uses_the_bytes_it_was_given_not_a_reserialised_body():
    """json.loads then json.dumps changes whitespace and key order, and the signature with it."""
    pretty = b'{ "id": "evt_1", "type": "deal.stage_changed" }'
    assert verify(SECRET, header(body=BODY), pretty, now=NOW) is False


def test_does_not_use_a_plain_equality_check(monkeypatch):
    """Constant-time comparison: hmac.compare_digest must be what decides."""
    calls = []
    real = hmac.compare_digest
    monkeypatch.setattr(hmac, "compare_digest", lambda a, b: calls.append(1) or real(a, b))
    verify(SECRET, header(), BODY, now=NOW)
    assert calls, "use hmac.compare_digest to compare signatures"
