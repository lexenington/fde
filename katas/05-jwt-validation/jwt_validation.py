"""Kata 5: validate an access token the way a security lead would check it.

You may use the `pyjwt` library (`import jwt`). The kata is knowing which options it needs, because its defaults
are not safe enough on their own.
"""

import time


class InvalidToken(Exception):
    """Raise this, and only this, for any token you reject."""


def validate(token: str, jwks: dict, *, issuer: str, audience: str, now: float | None = None, leeway: float = 30) -> dict:
    """Return the token's claims if, and only if, ALL of these hold:

    - it is signed with RS256 by a key in `jwks` (`{"keys": [{"kid": ..., "kty": "RSA", "n": ..., "e": ...}, ...]}`),
      chosen by the token's `kid` header (the IdP rotates keys, so there can be several)
    - `iss` equals `issuer`
    - `aud` contains `audience` (a string, or a list of strings)
    - `exp` is present and in the future, allowing `leeway` seconds of clock skew
    - `nbf`, if present, is not in the future (same leeway)

    Reject everything else with InvalidToken: tampered payloads, unknown keys, `alg: none`, an HS256 token "signed"
    with your public key, missing claims. `now` (seconds since the epoch) lets tests control the time; when it is
    None, use the real clock.

    Hint: pyjwt compares `exp` and `nbf` with the REAL clock, so it cannot honour `now` by itself. Keep its
    signature, algorithm, issuer and audience checks, and do the time checks yourself when `now` is given.
    """
    raise NotImplementedError
