# Implementation playbook: <product>

Living document. Update after every onboarding. The goal: each customer goes live faster than the last.

## Onboarding log
| Customer | Kickoff | Go-live | Days | Biggest time sink | What I'll do differently |
|---|---|---|---|---|---|

## Day 0: before kickoff
- [ ] Read the sales notes: what was promised, by whom, with what success metric
- [ ] Get access to: their help centre / knowledge base, ~200 recent real conversations, their ticketing / CRM system
- [ ] Skim 50 real conversations and tag them by intent. Top 10 intents = phase 1 scope

## Kickoff call (60 min)
- Success metric and target (automation rate, CSAT, response time), with today's baseline
- Top intents, and which ones are **off-limits** for automation
- Hard rules: money limits, regulated topics, identity checks. These become code, not prompts
- Escalation: to whom, through which tool, during which hours
- Tone and languages
- Their go-live date and why it matters

## Build (days 1–N)
| Step | Done how in our product | Typical time | Gotchas |
|---|---|---|---|
| Knowledge import + audit (gaps, contradictions) | | | |
| Agent instructions / procedures per intent | | | |
| Tools / integrations (order lookup, refunds, verification) | | | |
| Hard rules enforced in tools | | | |
| Escalation routing | | | |
| Scenario suite (≥ 25, from real conversations) | | | |

## Reusable assets
Connectors, instruction snippets, scenario templates and scripts that worked. Link them here, and turn any repeated one into a product feature.

## Common failure patterns and fixes
| Symptom | Usual cause | Fix |
|---|---|---|
| "The AI said something wrong" | Outdated or contradictory knowledge article | Fix the source; add a scenario |
| | | |
