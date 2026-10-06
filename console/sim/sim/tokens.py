"""Get real tokens from the customer's Keycloak, and make the bad ones an attacker would try."""

import base64
import json

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from . import config


class IdPError(Exception):
    pass


def get_token(user: str, client: str = "runmysales") -> str:
    url = f"{config.KEYCLOAK_INTERNAL_URL}/realms/{config.REALM}/protocol/openid-connect/token"
    try:
        r = httpx.post(url, timeout=10, data={
            "grant_type": "password", "client_id": client, "scope": "openid email profile",
            "username": config.USERS[user]["email"], "password": config.USER_PASSWORD,
        })
    except httpx.HTTPError as e:
        raise IdPError(f"Keycloak unreachable at {config.KEYCLOAK_INTERNAL_URL} ({type(e).__name__}). Is it still starting?")
    if r.status_code != 200:
        raise IdPError(f"Keycloak refused a token for {user}: {r.status_code} {r.text[:200]}")
    return r.json()["access_token"]


def decode(token: str) -> dict:
    return {"header": jwt.get_unverified_header(token), "payload": jwt.decode(token, options={"verify_signature": False})}


def _b64(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).rstrip(b"=").decode()


def tampered(token: str, **changes) -> str:
    """Same header and signature, edited payload. Signature check must fail."""
    h, _, s = token.split(".")
    payload = jwt.decode(token, options={"verify_signature": False})
    payload.update(changes)
    return f"{h}.{_b64(payload)}.{s}"


def forged(token: str) -> str:
    """Identical claims and kid, signed with a key the IdP never published."""
    parts = decode(token)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return jwt.encode(parts["payload"], key, algorithm="RS256", headers={"kid": parts["header"].get("kid")})


def alg_none(token: str) -> str:
    payload = jwt.decode(token, options={"verify_signature": False})
    return f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(payload)}."
