import hashlib
import hmac


def verify(secret: str, header: str, raw_body: bytes, *, now: float, tolerance: float = 300) -> bool:
    try:
        pairs = [p.split("=", 1) for p in header.split(",") if "=" in p]
        t = next(int(v) for k, v in pairs if k.strip() == "t")
        sigs = [v.strip() for k, v in pairs if k.strip() == "v1"]
    except (StopIteration, ValueError):
        return False
    if abs(now - t) > tolerance:
        return False
    expected = hmac.new(secret.encode(), f"{t}.".encode() + raw_body, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, s) for s in sigs)
