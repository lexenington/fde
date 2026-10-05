# 05 — Getting hired

## Positioning: one sentence

> **"Full-stack engineer who ships AI agents into messy, real-world environments — offline-first, mobile-money, WhatsApp-native — and measures that they work."**

That's differentiated. Most FDE applicants have never deployed into low-connectivity environments, local payment rails or multilingual users. You have. Lead with that, don't hide it.

## Target list (verify current openings: titles and policies change often)

| Tier | Who | Titles to search | Notes for you |
|---|---|---|---|
| **A: Reach** | Anthropic, OpenAI, Cohere, Mistral, Palantir | Forward Deployed Engineer, Applied AI Engineer, Solutions Engineer (Applied AI) | Usually hub-based (SF / NYC / London / EU) with travel. London/EU roles fit GMT. Check visa sponsorship per posting |
| **B: Sweet spot** | AI-native application companies: customer-service agents, legal, finance, search, voice | FDE, Deployment Engineer, Implementation Engineer, Solutions Engineer | Many are remote-friendly and hire via employer-of-record (Deel, Remote, Oyster) |
| **C: Platforms** | Databricks, Snowflake, Scale AI, MongoDB, cloud providers | Resident Solutions Architect, Customer Engineer | More data-heavy; 02/01 matters most |
| **D: Partners & consultancies** | AI implementation partners of the labs and clouds, large SIs' AI practices | AI Engineer, Delivery Engineer | Lower bar, real client work, great stepping stone |
| **E: Regional** | Companies building or deploying AI across Africa: fintechs, telcos, health, agritech | Applied AI / Solutions / Implementation | Your local context is a direct advantage here |

**Strategy:** apply to B, D and E in parallel from week ~10 to build interview reps and possibly land a role. Hold A until two case studies are published (~week 14).

### Remote-from-Ghana realities
- FDE is the *least* remote-friendly engineering role, because customers are physical. Expect postings to say "travel 25–50%" or "based in X."
- **Your timezone is an asset for London/EMEA teams.** Say so explicitly in applications.
- If a role requires relocation, check whether the company sponsors visas (e.g. UK Skilled Worker) before investing in the loop.
- Contract/EOR FDE work with a remote-first startup is a legitimate first step. One year of "Forward Deployed Engineer" on your CV changes every later application.

## Résumé rewrite

**Title:** `Forward Deployed / Applied AI Engineer`, not "Full-Stack Developer". Your title is a claim about what you do *next*.

**Rewrite every bullet as an outcome:**

| Before (feature) | After (FDE) |
|---|---|
| Built AI sales agent using Claude API tool use | Deployed an AI sales agent for ___ SMBs that qualified ___ inbound leads and booked ___ meetings via Claude tool use; designed human-escalation rules that kept ___% of conversations fully automated |
| Offline-first POS with Kitchen Display | Shipped an offline-first restaurant platform to ___ venues on unreliable connectivity, with zero lost orders across ___ hours of outages; integrated Mobile Money via Paystack |
| Managed data-capturing servers with Python/Selenium | Built and operated data-collection infrastructure processing ___ records/day for ___ clients at Verisage |

Add a **"Selected deployments"** section linking the module-04 case studies.

## Portfolio changes (lexenington.github.io/portfolio)
1. Replace the feature-list cards with **case-study cards**: outcome headline, constraint, metric.
2. Add one eval report (02/03 or engagement 1) as a page. Almost no candidates show one.
3. Add a 5-minute demo video per case study, showing the user's workflow first and architecture second.
4. Add a short "How I work with customers" section: discovery → scope → weekly demos → measure → hand over.
5. Move the Udacity course repos (`cd0157…`) off the front page. They signal "learner"; your case studies signal "deployer".

## The interview loop (typical shape; varies by company)

| Round | What they test | Prep |
|---|---|---|
| Recruiter / hiring-manager screen | Motivation, communication, "why FDE not SWE" | 2-minute story: problem-solver who goes where the problem is. Use EatryCloud |
| Practical coding | Working code under ambiguity, not leetcode puzzles: parse this messy file, call this API, handle errors | 02/01 lab under a timer; [question bank](interview-bank.md) |
| System design (customer flavour) | Design for *their* constraints: security, data residency, existing systems, rollout | Practise with engagement 2 out loud |
| **Decomposition / customer case** | Take a vague business problem, structure it, ask the right questions, pick an MVP, define success | The most important round. See the bank. Do 10 out loud |
| AI-specific (labs, AI startups) | Prompting, agent design, evals, failure modes, cost | 02/03 + your own RunMySales numbers |
| Behavioural | Ownership, ambiguity, conflict with customers, failure | 8 STAR stories, listed in the bank |
| Sometimes: take-home / presentation | Build a small thing, then present it to "the customer" | Treat it like engagement 1, compressed: scope doc + demo + eval |

## Practising
Use [practice-with-claude.md](practice-with-claude.md) for daily role-play reps (sceptical customer, decomposition interviewer, angry exec). Log every application in [applications.md](applications.md).

## Being findable
FDE hiring leans heavily on referrals and visible work. Cold applications alone are a slow path.
- **Write in public:** one short post per finished lab or engagement (what the problem was, what you measured, one surprise). LinkedIn plus your portfolio. Your case studies already cover the content; this is distribution.
- **Open-source an MCP server** for a system common in your region (e.g. a Mobile Money provider, a WhatsApp BSP, or an ERP like Odoo). It's useful, searchable and shows integration skill. People hiring FDEs look for exactly this.
- **Show up:** GDG Accra, local AI meetups, and online communities around Claude, MCP and AI engineering. Answering other people's integration questions is the fastest way to get noticed.
- **Referrals:** for every tier-A company, find one person in its deployment, solutions or applied AI team and ask a specific question about their work, not for a job. Ask for the referral after the conversation, not before.

## Certifications (optional signal, never a substitute for case studies)
- **AWS Solutions Architect – Associate:** the natural next step after your Cloud Practitioner; covers 02/04 directly.
- Anthropic's free courses (Anthropic Academy) on the API, tool use and MCP: cheap to do, and fine to list.
- Skip broad certificate collecting. One case study with a real metric is worth more than five badges.

## 30/60/90: what to say when asked "what would you do first?"
- **30 days:** Shadow 3+ customer deployments, ship one small fix to production, read every field-feedback note from the last quarter.
- **60 days:** Own one customer workstream end to end, write the first eval for it, file field feedback.
- **90 days:** Lead a deployment, turn one repeated workaround into a reusable tool or template for other FDEs.

## Timeline
| Week | Action |
|---|---|
| 1 | Rewrite résumé + portfolio copy (fill in the blanks with real numbers) |
| 10 | Start applying to tiers B, D, E. Aim for 5 quality applications/week, each with a 3-line note tied to their product |
| 12 | Mock interviews: decomposition ×5, system design ×3 (Pramp, peers, or ask Claude to role-play a sceptical customer) |
| 14 | Two case studies live → start tier A |
| 16 | Review: what are interviewers consistently probing? Feed that back into the gaps |
