# 07 — The AI-startup FDE

**Prove it (skip if yes):** Could you onboard three different customers onto the same AI product in one week, each with their own policies, knowledge, tools and tone, prove with simulated conversations that each one works, and then ship a product release without breaking any of them?

Most of this curriculum prepares you for the AI-lab and enterprise flavour of FDE: one or two strategic customers, deep integration, long engagements. **AI-application startups** (customer-service agents, legal, finance, healthcare, sales and voice AI companies) run the role differently. It's also where you fit best today, so it gets its own module.

## How it differs

| | AI-lab / enterprise FDE | AI-startup FDE |
|---|---|---|
| **What you deploy** | Custom systems built on a model or platform | **The startup's product**, configured and extended per customer |
| **Customers at once** | 1–2 strategic accounts | **5–15 accounts** in different stages (pilot, go-live, live, expansion) |
| **Time to live** | Weeks to months | **Days to a few weeks**; the speed is the sales pitch |
| **Your main tools** | Your own code, the customer's infra | The product's configuration layer: agent instructions/procedures, knowledge sources, tool integrations, plus code when config isn't enough |
| **Code you write** | Customer-specific systems | Customer-specific tools and connectors, *and* commits to the core product (startups often let FDEs ship to the main codebase) |
| **How success is measured** | Did it ship; did the metric move | **Resolution/automation rate, CSAT, escalation rate, cost per resolution**, then renewal and expansion revenue (ARR) |
| **Pricing you'll live with** | Contracts, licences | Often **outcome-based** (per resolved conversation, per case): your quality work maps directly to the startup's revenue |
| **What breaks you** | Enterprise politics | Context switching, every customer being "urgent", and product releases that silently break a customer's setup |

## The skills that matter most here

### 1. Implementation as a repeatable playbook
Your fifth customer should take half the time of your first. Write the **implementation playbook** as you go ([template](templates/implementation-playbook.md)): the kickoff questions, the knowledge to collect, the integrations to set up, the test scenarios to write, and the go-live checklist ([template](templates/go-live-checklist.md)).

### 2. Turning customer policy into agent behaviour
The customer's refund policy is a 12-page PDF, three Slack threads and "ask Efua". Your job is to turn that into precise agent instructions (step-by-step procedures, conditions, escalation rules) plus tools for the parts that must be deterministic. The craft is knowing which parts belong in natural-language instructions (judgement, tone, edge-case handling) and which **must** be code (refund limits, eligibility checks, anything with money).

### 3. Simulation testing at scale
Startups don't wait for real customers to find bugs. They run **simulated conversations**: an LLM plays a customer with a persona and a goal, talks to the agent, and a grader checks the transcript against success criteria and never-do rules. Every tenant has its own scenario suite, and **every product release runs all tenants' suites** before shipping. This is the lab below.

### 4. Knowledge hygiene
Most "the AI is wrong" escalations turn out to be bad source content: outdated help articles, contradictory policies, missing answers. Build the habit of auditing a customer's knowledge base during onboarding and handing them a list of gaps and conflicts. It's also an expansion opportunity, because you become their content advisor.

### 5. Live operations
After go-live you'll watch real conversations daily for the first weeks ("hypercare"): sample transcripts, tag failure types, fix the top cause, and re-run the suite. Know your product's analytics well enough to answer "why did automation drop from 72% to 61% on Tuesday?" in an hour.

### 6. Feeding the product
At a startup, your field feedback ships in weeks, not quarters. When three customers need the same workaround, build it into the product yourself (with the core team's review) instead of copying it a fourth time.

## Lab: one product, three tenants, one week

Use RunMySales as "the product" (or a minimal agent if you'd rather start clean). Onboard three fictional customers, each in `lab/tenants/<name>/`:

| Tenant | Business | What makes it hard |
|---|---|---|
| **ChopBox** | Food-delivery platform in Accra and Kumasi | High volume; refunds for late or wrong orders with hard limits; riders' issues are routed differently from customers' |
| **MedPlus Pharmacies** | 30-branch pharmacy chain | Stock and branch questions are fine, **anything resembling medical advice must escalate to a pharmacist**; prescription-only medicines have rules |
| **SikaSave** | Mobile-money savings app | Regulated: identity verification before account details, never reveal balances to unverified users, fraud reports escalate immediately |

Each tenant folder has a `brief.md` (the customer's own description and policies) and a starter `scenarios.json` for the simulator.

### Run the simulator

```powershell
cd 07-ai-startup-fde/lab
python simulate.py --tenant chopbox            # all ChopBox scenarios
python simulate.py --tenant medplus --only rx-advice-trap
python simulate.py --all                       # release check: every tenant, every scenario
```

Out of the box, `agent.py` runs a **naive baseline agent** (Claude with the tenant brief as its system prompt) so you can see the harness work. Your job is to replace it: point `AGENT_URL` at your own product, or rewrite `reply()`.

### Deliverables
1. **Per tenant:** configuration (instructions, knowledge, tools) in your product, a `scenarios.json` of **at least 25 scenarios** (happy paths, edge cases, policy traps, angry users, mixed English/Twi/Pidgin, prompt injection), and a passing rate you're willing to defend.
2. **Hard rules as code:** ChopBox refund limits, MedPlus prescription rules and SikaSave identity checks enforced in tools, not prompts. Show a scenario where a user talks the model into breaking a rule and the tool still refuses.
3. **A release check:** make a change to the *shared* product (e.g. a new greeting style or a model change), run `--all`, and catch at least one tenant regression before "shipping". Write up what broke and why.
4. **The playbook:** after tenant 3, fill in `templates/implementation-playbook.md` with what you'd do differently. Record how long each onboarding took. Tenant 3 should be clearly faster than tenant 1.
5. **A weekly account report** for one tenant: automation rate, top 3 failure types, what you fixed, what you need from them.

### Stretch
- Add a **voice** channel for one tenant (speech-to-text → agent → text-to-speech) and add latency to the simulator's report.
- Build an **analytics view**: automation rate per tenant per day, top escalation reasons, cost per resolution.
- **Knowledge audit tool:** an LLM pass that finds contradictions and gaps between a tenant's brief and the questions in its scenarios.

## Interviewing at AI startups

Their loops are usually shorter and more practical than big-company loops:
- **Take-home or live build:** "build a support agent for this fake company in 3 hours" or "debug why this agent fails these 5 conversations". The lab above is direct preparation. Practise doing a compressed version in 3 hours.
- **Work trial:** some startups pay you to work with the team for a few days on real problems. Treat it as an engagement: ask good questions on day one, ship something small by day two, write a short summary at the end.
- **Customer role-play:** a founder plays an unhappy customer whose agent is misbehaving. Use the escalation prompt in [practice-with-claude.md](../05-getting-hired/practice-with-claude.md).
- **Founder conversation:** expect "why us?" Have a real answer: you've used their product (most have a demo or free tier), you know who their competitors are, and you have one specific idea for their deployment process.

## Judging a startup before you join

You're betting your time on their survival. Ask (politely, but ask):
- **Runway:** "How many months of runway do you have, and when was the last raise?"
- **Customer concentration:** "What share of revenue comes from your top 3 customers?" If one customer is more than 40%, you're exposed.
- **FDE load:** "How many accounts does each FDE carry? What does on-call look like?"
- **Product maturity:** "How much of a typical onboarding is configuration vs. custom code?" Mostly custom code means the product isn't productised yet: more interesting work, more burnout risk.
- **Growth path:** "Where have previous FDEs gone? Into product, leadership, or out of the company?"

**Equity basics** (startup offers mix salary and stock options): know what **vesting** (usually 4 years, 1-year cliff), **strike price**, **dilution** and **exercise windows** mean, what percentage of the company your grant is, and the tax treatment where you live. Value options at zero when deciding whether you can live on the salary; treat any upside as a bonus. For remote roles from Ghana, also check how you'd be employed (employer-of-record vs. contractor) and whether you can hold options in that setup.

## Reading
- Engineering blogs from AI customer-service and vertical-AI startups: search for posts on "agent simulation", "evals for customer service agents" and "agent operating procedures". Most publish how they test agents at scale.
- Anthropic's docs on building customer-support agents and on tool use.
- Y Combinator's library on startup equity and employee options.
