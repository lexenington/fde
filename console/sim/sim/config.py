"""Settings for the customer simulator. Defaults match docker-compose.yml; override with env vars."""

import os
from pathlib import Path

CRM_API_KEY = os.environ.get("CRM_API_KEY", "crm-dev-key")
CRM_WEBHOOK_SECRET = os.environ.get("CRM_WEBHOOK_SECRET", "whsec_dev_adom")
SCIM_TOKEN = os.environ.get("SCIM_TOKEN", "scim-dev-token")

# How the simulator reaches the learner's app (from inside Docker, the host is host.docker.internal)
LEARNER_URL = os.environ.get("LEARNER_URL", "http://host.docker.internal:8000")

# Keycloak: the simulator talks to it on the Docker network, but tokens carry the public issuer
KEYCLOAK_INTERNAL_URL = os.environ.get("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")
KEYCLOAK_PUBLIC_URL = os.environ.get("KEYCLOAK_PUBLIC_URL", "http://localhost:8081")
REALM = os.environ.get("KEYCLOAK_REALM", "adom")
USER_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "Passw0rd!")

# Where checker runs are written. Mounted to the lab folders, so runs are committed as evidence
_here = Path(__file__).resolve()
LABS_DIR = Path(os.environ["LABS_DIR"]) if "LABS_DIR" in os.environ else _here.parents[3] / "02-technical-depth"

# Stakeholder briefs and inject cards. The learner must not read these: they hold the hidden facts
CONTENT_DIR = Path(os.environ.get("CONTENT_DIR", _here.parents[1] / "content"))
# Call transcripts and debriefs are saved here (committed = evidence of reps)
PRACTICE_DIR = Path(os.environ["PRACTICE_DIR"]) if "PRACTICE_DIR" in os.environ else _here.parents[3] / "03-customer-craft" / "practice"

KEYCLOAK_ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin")

RATE_LIMIT_PER_SEC = float(os.environ.get("CRM_RATE_LIMIT_PER_SEC", "5"))
RATE_LIMIT_BURST = int(os.environ.get("CRM_RATE_LIMIT_BURST", "10"))

USERS = {
    "kofi": {"email": "kofi.mensah@adom.example", "name": "Kofi Mensah", "group": "sales-reps"},
    "ama": {"email": "ama.owusu@adom.example", "name": "Ama Owusu", "group": "sales-reps"},
    "efua": {"email": "efua.asante@adom.example", "name": "Efua Asante", "group": "sales-managers"},
    "yaw": {"email": "yaw.boateng@adom.example", "name": "Yaw Boateng", "group": "sales-reps", "note": "exists in the IdP but is never provisioned to your app"},
}
