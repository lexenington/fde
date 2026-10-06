# 01 — Gap analysis: you vs. the FDE bar

Based on your portfolio (lexenington.github.io/portfolio), October 2026.

## What you already have (don't spend time here)

| FDE requirement | Your evidence | Strength |
|---|---|---|
| Ship full-stack products end to end | EatryCloud, RunMySales, Webfront360, 7+ yrs at Verisage | **Strong** |
| Python + TypeScript fluency | Django, Flask, Next.js, Remix, Hono | **Strong** |
| LLM tool use / agents | RunMySales: Claude tool use, booking, human escalation | **Strong**, and rare |
| Messy real-world constraints | Offline-first POS, thermal printers, Mobile Money via Paystack | **Strong** (great interview stories) |
| Data collection at scale | Selenium data-capture servers at Verisage | Medium |
| Containers & cloud | Docker, K8s, AWS (Cloud Practitioner), Railway | Medium |
| Working with clients | 10 yrs freelance (school mgmt system, WordPress, APIs) | Medium. Real, but SMB-scale |
| Async/jobs/real-time | BullMQ, Socket.io, PowerSync | Strong |

## The gaps, ranked by how often they sink candidates like you

### 1. Measured AI in production (evals) — **critical**
You can build an agent. The FDE question is: *"How do you know it works, how would you know when it stops working, and what's the error rate on the cases the customer cares about?"* Most full-stack devs answer with vibes. You need eval sets, graders, regression runs, and a number.
→ [02/03 AI engineering](../02-technical-depth/03-ai-engineering/README.md)

### 2. Enterprise integration surface — **critical**
Your integrations so far are developer-friendly APIs (Paystack, Claude). Enterprise customers bring SAML/OIDC SSO, SCIM provisioning, Salesforce/ServiceNow/SAP/Zendesk, Snowflake shares, IP allow-lists, service accounts nobody can find the owner of, and security questionnaires.
→ [02/02 Enterprise integration](../02-technical-depth/02-enterprise-integration/README.md)

### 3. Data you didn't design — **high**
In your products you own the schema. At a customer, you inherit three systems that disagree about what a "customer" is. Entity resolution, reconciliation, and data-quality reporting are daily FDE work.
→ [02/01 Messy data](../02-technical-depth/01-messy-data/README.md)

### 4. Enterprise-grade discovery & scoping — **high**
Freelance clients tell you what to build. Enterprise sponsors often don't know, disagree with each other, or describe a solution instead of a problem. You need to run discovery, write a scoping doc with success metrics, and manage scope in writing.
→ [03 Customer craft](../03-customer-craft/README.md)

### 5. Deploying into someone else's infra — **medium**
Railway and your own AWS are your turf. FDEs deploy into the customer's AWS/GCP/Azure account, inside their VPC, sometimes with no public internet, through their change-management process. That calls for Terraform, private networking, secrets management and observability you hand over.
→ [02/04 Deploy anywhere](../02-technical-depth/04-deploy-anywhere/README.md)

### 6. Impact narrative — **medium, cheap to fix**
Your portfolio lists *features* ("offline-first POS, Kitchen Display…"). FDE hiring managers read for *outcomes* ("cut order-to-kitchen time from X to Y for N restaurants"). Fix this first, in a weekend.
→ [05 Getting hired](../05-getting-hired/README.md)

## Reframe your existing projects now (FDE language)

Rewrite each project as **Situation → Constraint → What I built → Measured result → What I'd do differently**. Fill in real numbers; if you don't have them, go and get them (usage logs, client emails).

**RunMySales (draft — fill the blanks)**
> Small businesses were losing inbound leads outside working hours. I built an AI sales agent that qualifies leads, handles objections and books appointments through Claude tool use, with automatic escalation to a human when confidence is low or the lead asks. Across ___ businesses it handled ___ conversations, booked ___ meetings, and escalated ___%. The hardest problem was ___ (e.g. knowing *when* to escalate), which I solved by ___.

**EatryCloud**
> Restaurants in Ghana run on unreliable connectivity and Mobile Money. I built an offline-first POS (PowerSync) with kitchen display and thermal printing, syncing to the cloud when online, with Paystack MoMo payments. ___ restaurants, ___ orders/day, zero lost orders during ___ hours of outages.

Offline-first, flaky connectivity and local payment rails are **exactly** the kind of "deploy into a hostile environment" story FDE interviewers love. Lead with it.

**Verisage**
> Pull out one engagement where you worked directly with a stakeholder to define the problem. That becomes your "tell me about a time the requirements were wrong" answer.

## Exercise

Open [self-assessment.md](self-assessment.md). Score yourself 1–5 on every row **now** (week 1), then again at weeks 8 and 16, with a link or file as evidence for any 4 or 5. The full list lives there, and it is longer than the summary you'd write from memory: that is deliberate.
