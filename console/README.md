# FDE Field Console

The customer's world, on your machine. One command brings up the systems a real customer would point you at, a web Console to watch and poke them, and checkers that drive **your** lab code through them and score it.

```powershell
cd console
docker compose up --build        # first boot takes a few minutes; Keycloak needs ~30s after that
```

Then open **http://localhost:3300**.

| Service | URL | What it is |
|---|---|---|
| Console | http://localhost:3300 | Dashboard, lab briefs, checker runs and history, CRM and IdP views |
| Customer simulator | http://localhost:8090 (API docs at `/docs`) | Adom Logistics' CRM API (`/crm/v3`), webhooks, rate limits, the lab checkers |
| Customer IdP | http://localhost:8081 (admin / admin) | Keycloak, standing in for Okta / Entra ID. Realm `adom` |
| **Your app** | http://localhost:8000 | Not in this stack. You build and run it yourself, in the lab folder |

## The one rule

The Console plays the **customer** and the **grader**. It never contains your solution. Your code lives in the lab folders, runs on your machine, and gets committed with its run files (`lab/runs/*.json`), so your git history shows the score going up.

## A working session

1. Open the lab in the Console and read the **Contract** tab. Write `SCOPE.md` first.
2. Build one capability, then **Run checker**. Only the first failure shows its hint. Fix that before you read the next one (tick "show every hint" if you're stuck).
3. Use the customer's systems by hand: change a deal stage in the **CRM** page (it sends your app a signed webhook), arm 429s, get a token for a user on the **Identity** page and curl your API with it.
4. Commit your code *and* the new run file.

From the terminal instead of the UI:

```powershell
docker compose exec sim python -m sim.checks integration
```

## Labs in the Console

| Lab | Status |
|---|---|
| 02 Enterprise integration | **Live**: OIDC, SCIM, roles, CRM sync, webhooks (22 checks) |
| 01 Messy data, 03 AI engineering | Still terminal-based (`check.py`, `eval.py`) |
| Stakeholder chat, inject cards, engagement worlds | Next slices |

## Troubleshooting

- **"Your app" is red on the dashboard.** Start your app on port 8000 and make it listen on `0.0.0.0` (or at least accept connections from Docker). On the CRM page you can change the URL the simulator uses. From inside Docker, your machine is `host.docker.internal`.
- **Token errors right after `up`.** Keycloak is still starting; wait for its dot on the dashboard to go green.
- **Issuer mismatch.** Tokens always carry `iss = http://localhost:8081/realms/adom`, whether they were fetched from your machine or from inside Docker. Validate against exactly that.
- **Start again from scratch.** `docker compose down` resets Keycloak and the CRM (everything lives in memory). Your app's own database is yours to reset.

## Developing the Console itself

- **Simulator:** `cd sim`, then `pip install -r requirements.txt`, `python -m pytest -q`, and `uvicorn sim.app:app --port 8090 --reload`.
- **UI:** `cd ui`, then `npm install` and `npm run dev`. It serves on :3300 and proxies to the simulator at `SIM_INTERNAL_URL`, which defaults to `http://localhost:8090`.
- **Adding a lab checker:** write a `Suite` in `sim/sim/checks/`, register it in `checks/__init__.py`, and add a page under `ui/app/labs/`.
