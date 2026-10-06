import base64
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from jwt_validation import InvalidToken, validate

ISS, AUD = "http://localhost:8081/realms/adom", "runmysales"
NOW = 1_790_000_000


def make_key(kid):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    pub_jwk.update(kid=kid, alg="RS256", use="sig")
    return key, pub_jwk


@pytest.fixture(scope="module")
def keys():
    k1, j1 = make_key("key-1")
    k2, j2 = make_key("key-2")
    return {"key-1": k1, "key-2": k2, "jwks": {"keys": [j1, j2]}, "public_pem": k1.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)}


def token(keys, kid="key-1", **overrides):
    claims = {"iss": ISS, "aud": AUD, "sub": "u1", "email": "kofi@adom.example", "exp": NOW + 300, "iat": NOW - 10}
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    pem = keys[kid].private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


def check(keys, tok, **kw):
    return validate(tok, keys["jwks"], issuer=ISS, audience=AUD, now=NOW, **kw)


def test_a_good_token_returns_its_claims(keys):
    claims = check(keys, token(keys))
    assert claims["email"] == "kofi@adom.example" and claims["aud"] == AUD


def test_the_right_key_is_chosen_by_kid(keys):
    assert check(keys, token(keys, kid="key-2"))["sub"] == "u1"


def test_an_audience_list_that_contains_ours_is_fine(keys):
    assert check(keys, token(keys, aud=["account", AUD]))["sub"] == "u1"


def test_another_apps_token_is_rejected(keys):
    with pytest.raises(InvalidToken):
        check(keys, token(keys, aud="other-app"))
    with pytest.raises(InvalidToken):
        check(keys, token(keys, aud=["account", "other-app"]))


def test_the_wrong_issuer_is_rejected(keys):
    with pytest.raises(InvalidToken):
        check(keys, token(keys, iss="http://evil.example/realms/adom"))


def test_expired_tokens_are_rejected_beyond_the_leeway(keys):
    with pytest.raises(InvalidToken):
        check(keys, token(keys, exp=NOW - 31))
    assert check(keys, token(keys, exp=NOW - 10))          # inside the 30 s leeway
    with pytest.raises(InvalidToken):
        check(keys, token(keys, exp=NOW - 10), leeway=5)


def test_a_token_that_is_not_valid_yet_is_rejected(keys):
    with pytest.raises(InvalidToken):
        check(keys, token(keys, nbf=NOW + 600))


def test_a_token_without_an_expiry_is_rejected(keys):
    with pytest.raises(InvalidToken):
        check(keys, token(keys, exp=None))


def test_a_missing_audience_or_issuer_is_rejected(keys):
    for missing in ({"aud": None}, {"iss": None}):
        with pytest.raises(InvalidToken):
            check(keys, token(keys, **missing))


def test_a_tampered_payload_is_rejected(keys):
    h, p, s = token(keys).split(".")
    payload = json.loads(base64.urlsafe_b64decode(p + "=="))
    payload["email"] = "efua@adom.example"
    forged = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    with pytest.raises(InvalidToken):
        check(keys, f"{h}.{forged}.{s}")


def test_a_token_signed_by_an_unknown_key_is_rejected(keys):
    rogue, _ = make_key("key-1")                            # same kid, different key
    pem = rogue.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    forged = jwt.encode({"iss": ISS, "aud": AUD, "exp": NOW + 300}, pem, algorithm="RS256", headers={"kid": "key-1"})
    with pytest.raises(InvalidToken):
        check(keys, forged)


def test_an_unknown_kid_is_rejected(keys):
    pem = keys["key-1"].private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    tok = jwt.encode({"iss": ISS, "aud": AUD, "exp": NOW + 300}, pem, algorithm="RS256", headers={"kid": "key-99"})
    with pytest.raises(InvalidToken):
        check(keys, tok)


def test_alg_none_is_rejected(keys):
    def b64(o): return base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()
    tok = f"{b64({'alg': 'none', 'typ': 'JWT', 'kid': 'key-1'})}.{b64({'iss': ISS, 'aud': AUD, 'exp': NOW + 300})}."
    with pytest.raises(InvalidToken):
        check(keys, tok)


def test_hs256_signed_with_the_public_key_is_rejected(keys):
    """The classic algorithm-confusion attack: treat the public key as an HMAC secret."""
    import hashlib, hmac
    def b64(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": "key-1"}).encode())
    body = b64(json.dumps({"iss": ISS, "aud": AUD, "exp": NOW + 300}).encode())
    sig = b64(hmac.new(keys["public_pem"], f"{head}.{body}".encode(), hashlib.sha256).digest())
    with pytest.raises(InvalidToken):
        check(keys, f"{head}.{body}.{sig}")


@pytest.mark.parametrize("junk", ["", "abc", "a.b.c", "a.b", None])
def test_garbage_is_rejected_with_invalid_token_not_a_crash(keys, junk):
    with pytest.raises(InvalidToken):
        check(keys, junk)


def test_uses_the_real_clock_when_now_is_none(keys):
    real = jwt.encode({"iss": ISS, "aud": AUD, "exp": time.time() + 300},
                      keys["key-1"].private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()),
                      algorithm="RS256", headers={"kid": "key-1"})
    assert validate(real, keys["jwks"], issuer=ISS, audience=AUD)["iss"] == ISS
