# FDE curriculum repo

Personal curriculum for moving from full-stack engineer to Forward Deployed Engineer. The learner is an experienced engineer (7+ yrs, Python/TS, own AI products); keep everything at that level and in a Ghana / West Africa context where it fits.

## How to help in this repo
- **Coach, don't do the labs.** For lab and engagement work, review, question and point at problems. Only write solution code when explicitly asked. The point is the learner's own reps.
- Role-play prompts live in `05-getting-hired/practice-with-claude.md`. When asked to role-play, stay in character until told to stop, then give scored feedback.
- Track progress in `PROGRESS.md`; update checkboxes when asked.

## Commands
- Activate env: `.\.venv\Scripts\Activate.ps1`
- Messy-data lab: `python make_messy_data.py`, then `python check.py out/clusters.json` (in `02-technical-depth/01-messy-data/lab`)
- Katas: `python -m pytest -q katas/NN-name` from the repo root (`pip install -r requirements.txt`). Tests are the spec; don't edit them, and coach rather than solve. Reference solutions are deliberately not in the learner-visible folders (`console/sim/content/katas/solutions/`, used only by the simulator's tests; don't open them to answer)
- AI lab: `python eval.py` (needs `ANTHROPIC_API_KEY`), and `python -m pytest -q` for grader tests (no key needed), in `02-technical-depth/03-ai-engineering/lab`
- AI-startup lab: `python simulate.py --tenant <chopbox|medplus|sikasave>` or `--all` (needs `ANTHROPIC_API_KEY`), in `07-ai-startup-fde/lab`
- Field Console (simulated customer + checkers): `docker compose up --build` in `console/`, UI on http://localhost:3300; terminal checker: `docker compose exec sim python -m sim.checks integration`. Simulator tests: `python -m pytest -q` in `console/sim`
- Engagement worlds (Lakeside, Savanna): the contract for each is `04-engagements/<name>/WORLD.md`; the customer's systems and the hidden acceptance test run in the Console. Runs are saved to `04-engagements/<name>/runs/`
- Console UI dev: `npm run dev` in `console/ui` (needs the simulator on :8090)

## Conventions
- Never open or print `.truth/` in the messy-data lab: it's the hidden answer key. The same goes for `console/sim/content/`: stakeholder hidden facts, card effects and rubrics.
- The Console plays the customer and the grader. Never add lab solutions to `console/` (no reference implementations of the learner's app).
- Every lab ends with a short report written for its stated audience (ops manager, CFO, IT lead), not for engineers.
