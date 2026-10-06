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

## Practice tools

| Page | What it does | Needs |
|---|---|---|
| **Stakeholder calls** | Ten people across three customers (Adom, Lakeside, Savanna), played by Claude. Each knows things you don't and only says them when you ask well. Ends with a scored debrief: six skills, which hidden facts you found and missed, the exact question that would have unlocked each miss, and your talk ratio. The transcript is saved to `03-customer-craft/practice/` | `ANTHROPIC_API_KEY` |
| **Inject cards** | Six mid-lab curveballs for 02/02. Four change the customer's systems (CRM quota cut, duplicate and late webhooks, secret rotation, an IdP claim change), each with a one-click check that tests whether your app copes. Every card also asks for a written reply that Claude reviews against a rubric. Everything is saved in `02-technical-depth/02-enterprise-integration/lab/injects/` | `ANTHROPIC_API_KEY` for the feedback; the checks work without it |

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."     # before `docker compose up`, in the same terminal
docker compose up --build
```

Calls and reviews default to `claude-opus-5-5`. Set `FDE_CHAT_MODEL` / `FDE_JUDGE_MODEL` in `docker-compose.yml` (for example `claude-sonnet-5-5`) to cut cost. A full call plus debrief is a few tens of thousands of tokens.

**Don't read `sim/content/`.** It holds the stakeholders' hidden facts and the cards' effects and rubrics. It is the answer key, like `.truth/` in the messy-data lab.

**When a card has changed something**, a yellow banner on the lab page says so, so a failing checker is never a mystery. *Clear conditions* undoes every card's effect, including the IdP's claim format.

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
| Stakeholder calls and inject cards | **Live** |
| Engagement worlds (Lakeside's legacy database and WhatsApp, Savanna's documents) | Next slice |

## Troubleshooting

- **"Your app" is red on the dashboard.** Start your app on port 8000 and make it listen on `0.0.0.0` (or at least accept connections from Docker). On the CRM page you can change the URL the simulator uses. From inside Docker, your machine is `host.docker.internal`.
- **Token errors right after `up`.** Keycloak is still starting; wait for its dot on the dashboard to go green.
- **Issuer mismatch.** Tokens always carry `iss = http://localhost:8081/realms/adom`, whether they were fetched from your machine or from inside Docker. Validate against exactly that.
- **"ANTHROPIC_API_KEY is not set".** Export it in the shell where you run `docker compose up`, then `docker compose up -d sim`. The dashboard shows a Claude light.
- **A call disappeared.** Active calls live in the simulator's memory, so restarting it ends them. Transcripts are only saved when you end a call and read the debrief.
- **Start again from scratch.** `docker compose down` resets Keycloak and the CRM (everything lives in memory). Your app's own database is yours to reset.

## Developing the Console itself

- **Simulator:** `cd sim`, then `pip install -r requirements.txt`, `python -m pytest -q`, and `uvicorn sim.app:app --port 8090 --reload`.
- **UI:** `cd ui`, then `npm install` and `npm run dev`. It serves on :3300 and proxies to the simulator at `SIM_INTERNAL_URL`, which defaults to `http://localhost:8090`.
- **Tests use a scripted fake instead of Claude** (`llm.set_backend`), so `python -m pytest -q` needs no API key and costs nothing.
- **Adding a stakeholder:** add a character to a JSON file in `sim/content/stakeholders/` (the content test checks the shape). **Adding a card:** add it to `sim/content/injects/<lab>.json`; a new effect or check goes in `sim/sim/injects.py`.
- **Adding a lab checker:** write a `Suite` in `sim/sim/checks/`, register it in `checks/__init__.py`, and add a page under `ui/app/labs/`.
