"""Changes the customer's IdP configuration, the way an IT team would over a weekend."""

import httpx

from . import config


class IdPAdminError(Exception):
    pass


def _admin_token(c: httpx.Client) -> str:
    r = c.post(f"{config.KEYCLOAK_INTERNAL_URL}/realms/master/protocol/openid-connect/token", data={
        "grant_type": "password", "client_id": "admin-cli",
        "username": config.KEYCLOAK_ADMIN_USER, "password": config.KEYCLOAK_ADMIN_PASSWORD})
    if r.status_code != 200:
        raise IdPAdminError(f"Keycloak admin login failed ({r.status_code})")
    return r.json()["access_token"]


def set_groups_full_path(enabled: bool, client_id: str = "runmysales") -> None:
    """Switch the `groups` claim between 'sales-managers' and '/sales-managers'."""
    base = f"{config.KEYCLOAK_INTERNAL_URL}/admin/realms/{config.REALM}"
    try:
        with httpx.Client(timeout=15) as c:
            c.headers["authorization"] = f"Bearer {_admin_token(c)}"
            clients = c.get(f"{base}/clients", params={"clientId": client_id}).json()
            if not clients:
                raise IdPAdminError(f"client {client_id} not found in realm {config.REALM}")
            uuid = clients[0]["id"]
            mapper = next((m for m in clients[0].get("protocolMappers", []) if m["name"] == "groups"), None)
            if not mapper:
                raise IdPAdminError("groups mapper not found")
            mapper["config"]["full.path"] = "true" if enabled else "false"
            r = c.put(f"{base}/clients/{uuid}/protocol-mappers/models/{mapper['id']}", json=mapper)
            if r.status_code not in (200, 204):
                raise IdPAdminError(f"could not update the mapper ({r.status_code}): {r.text[:200]}")
    except httpx.HTTPError as e:
        raise IdPAdminError(f"Keycloak unreachable ({type(e).__name__}). Is it still starting?")
