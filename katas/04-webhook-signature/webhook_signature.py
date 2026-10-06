"""Kata 4: verify a webhook signature.

Anyone can POST to your webhook URL. The signature is how you know it came from the provider, and the timestamp is
how you know it is not a recording of something that came from the provider last week.
"""


def verify(secret: str, header: str, raw_body: bytes, *, now: float, tolerance: float = 300) -> bool:
    """Return True only if the request is authentic and fresh.

    `header` looks like `t=1790000000,v1=<hex>` and may carry several `v1=` entries (during a secret rotation the
    provider signs with the old and new secret). Each `v1` is the hex HMAC-SHA256, keyed with a secret, of
    `f"{t}."` followed by the raw request body.

    Return True if ANY `v1` matches AND `abs(now - t) <= tolerance`. Return False, never raise, for anything
    malformed. Compare signatures in constant time.
    """
    raise NotImplementedError
