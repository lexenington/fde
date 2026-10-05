# Progress

Started: ____  ·  Target finish: ____ (≈16 weeks)

## Phase 1: Orient (week 1)
- [ ] Read 00 The role
- [ ] Collect 10 FDE postings + SUMMARY.md table
- [ ] Read 01 Gap analysis
- [ ] Self-assessment scores (baseline) in `01-gap-analysis/self-assessment.md`
- [ ] Rewrite RunMySales / EatryCloud / Verisage in outcome language with real numbers
- [ ] Update résumé + portfolio copy (05 → "Résumé rewrite")

## Phase 2: Technical depth (weeks 2–8)
### 02/01 Messy data
- [ ] SCOPE.md · [ ] profile.md · [ ] pipeline → Postgres · [ ] F1 ≥ 0.92 (`check.py`) · [ ] review queue < 10% · [ ] REPORT.md for ops manager · [ ] stretch: incremental load
### 02/02 Enterprise integration
- [ ] OIDC SSO (Okta/Entra) · [ ] SCIM provision/deprovision · [ ] group → role mapping · [ ] idempotent CRM sync · [ ] signed webhooks + DLQ · [ ] reconciliation job · [ ] audit log · [ ] SECURITY.md · [ ] 5 acceptance tests green
### 02/03 AI engineering & evals
- [ ] Baseline run + failure notes · [ ] gold set ≥ 30 docs · [ ] CHANGELOG with metric deltas · [ ] threshold table (auto % vs error %) · [ ] 4 injection cases pass · [ ] cost per 1,000 docs · [ ] REPORT.md for CFO
### 02/04 Deploy anywhere
- [ ] Customer + vendor AWS accounts · [ ] cross-account role policy · [ ] Terraform private deploy · [ ] OIDC CI deploy · [ ] dashboard + alarms · [ ] teardown/rebuild < 30 min · [ ] RUNBOOK.md · [ ] HANDOVER.md
### 02/05 Unfamiliar territory
- [ ] Ramp #1 (ARCHITECTURE · GLOSSARY · DATA-MAP · change + test · RAMP-LOG) · [ ] Ramp #2, faster
### Extras
- [ ] Invoice extractor wrapped as an MCP server · [ ] grader tests green (`pytest`) · [ ] Twi/code-switched eval slice (engagement 1)

## Phase 3: Customer craft (weeks 2–8, in parallel)
- [ ] Read *The Mom Test*
- [ ] Mock discovery calls: ☐1 ☐2 ☐3 ☐4 ☐5 ☐6
- [ ] Scoping docs written within 24 h: ☐1 ☐2 ☐3 ☐4 ☐5 ☐6
- [ ] 90-second exec explanation recorded
- [ ] Real SME discovery call done
- [ ] Business case written for one engagement (template)
- [ ] Role-play reps with Claude (practice-with-claude.md): ☐ discovery ☐ decomposition ☐ angry exec

## Phase 4: Engagements (weeks 9–14)
- [ ] 1 Lakeside Clinics: scope · build · eval · demo · case study published
- [ ] 2 Savanna Microfinance: scope · build · eval · deploy · case study published
- [ ] 3 Real customer: discovery · baseline · live · 2 wks measured · testimonial · case study published

## Phase 5: Hired (weeks 10–16+)
- [ ] Self-assessment re-score (week 8) · [ ] (week 16)
- [ ] 8 STAR stories written
- [ ] 10 decomposition prompts answered out loud
- [ ] Mock interviews: ☐ decomposition ×5 ☐ system design ×3 ☐ coding ×3
- [ ] Applications log started (`05-getting-hired/applications.md`)
- [ ] Tier B/D/E applications: ___  ·  Tier A applications: ___
- [ ] Visibility: ☐ 3 posts published ☐ open-source MCP server ☐ 1 meetup ☐ 3 referral conversations
- [ ] Offer 🎯

## 07 AI-startup FDE (before tier-B applications)
- [ ] Baseline simulator run (`python simulate.py --all`) and failures read
- [ ] ChopBox: config · ≥25 scenarios · hard rules in tools · passing bar · onboarding time ___ days
- [ ] MedPlus: config · ≥25 scenarios · hard rules in tools · passing bar · onboarding time ___ days
- [ ] SikaSave: config · ≥25 scenarios · hard rules in tools · passing bar · onboarding time ___ days
- [ ] Shared-product change caught a tenant regression via `--all` (write-up)
- [ ] Implementation playbook filled in · [ ] weekly account report for one tenant
- [ ] 3-hour "build a support agent" timed practice
- [ ] Startup due-diligence questions + equity basics ready for offers

## AWS FDE track (weeks 6–16, in parallel)
- [ ] Ground: ontology.md · machine-usable ontology · eval with vs. without ontology
- [ ] Orchestrate: per-user identity on tool calls · crash-and-resume without duplicate writes · approval gate
- [ ] Prove: policy-as-code that survives a jailbreak in the eval
- [ ] AWS variant: ☐ Bedrock + Guardrails extractor ☐ AgentCore + Strands agent ☐ Bedrock Knowledge Bases comparison
- [ ] Process map done for engagements: ☐1 ☐2 ☐3
- [ ] AIP-C01 booked · [ ] AIP-C01 passed

## Phase 6: Beyond (ongoing)
- [ ] Chosen direction for Webfront360 · [ ] 10 discovery calls · [ ] findings doc · [ ] business case · [ ] go / no-go
