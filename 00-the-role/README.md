# 00 — The role

## Where it came from

Palantir invented the title. Their "Delta" engineers embedded with government and enterprise customers, writing whatever code it took to make the platform solve that customer's actual problem. Their "Echo" counterparts owned the customer relationship and the problem definition. The model worked because the hardest part of enterprise software is rarely the product. It's **last-mile fit**: the data is wrong, the systems don't talk, and the real problem isn't the one in the RFP.

From 2023 the AI labs and AI-native startups adopted the title at scale, for the same reason. A frontier model is a general capability. Turning it into a working claims-triage system inside an insurer is a deployment problem.

## The three flavours you'll see in job posts

| Flavour | Examples (verify current openings) | What you actually do | Weighting |
|---|---|---|---|
| **Platform FDE** | Palantir, Databricks (Resident SA), Snowflake, Scale AI | Make the company's platform work on a big customer's data. Heavy data modelling and pipelines | Data eng 50 / Customer 30 / App 20 |
| **AI-lab FDE / Applied AI engineer** | Anthropic, OpenAI, Cohere, Mistral | Help strategic customers build production LLM systems: agents, RAG, evals. Feed patterns back to research and product | AI eng 50 / Customer 35 / Infra 15 |
| **AI-startup FDE** | Sierra, Decagon, Harvey, Glean, Hebbia, and many Series A–C companies | Configure and extend the product per customer. Often you *are* the implementation team | App/integration 40 / AI 30 / Customer 30 |

You fit best with **AI-startup FDE** today and with **AI-lab FDE** in 3–4 months. RunMySales is basically a Sierra/Decagon-style product you built yourself. Each flavour has dedicated material: AI-startup in [07](../07-ai-startup-fde/README.md), AI-lab and enterprise across 02–04, and the cloud-platform (AWS) version in the [AWS FDE track](../aws-fde-track/README.md).

## A realistic week

- **Mon:** Weekly sync with the customer's sponsor (VP Ops). Demo of last week's increment. Two new asks; you push one to next phase, in writing.
- **Tue:** Their IT team still hasn't given you read access to the Snowflake share. You write the exact grant statement they need to run, plus a one-paragraph security justification. Meanwhile you build against a sampled CSV export.
- **Wed:** Eval run shows the agent mis-routes 8% of refund requests. Root cause: their policy doc contradicts their macros. You write it up for the customer. The fix is *theirs* to decide, not yours.
- **Thu:** Pair with the customer's in-house engineer so they can own the deployment after you leave. Write the runbook.
- **Fri:** Write internal feedback for your own product team: "Three customers have now needed a per-tenant PII redaction step. Here's the shape it should take."

Notice that maybe 50% of that is code. The rest is unblocking, scoping, measuring and writing, and that's where full-stack devs most often fall short in FDE interviews.

## How FDEs are evaluated (on the job, and therefore in interviews)

1. **Time-to-value.** How fast does the customer see something real? (Days, not quarters.)
2. **Production outcomes.** Did it go live? Is it still running 90 days later? What metric moved?
3. **Scope judgment.** Did you build what mattered, and say no to the rest?
4. **Customer trust.** Do their engineers and execs ask for you by name?
5. **Product leverage.** Did what you learned in the field make the core product better?

## FDE vs. neighbouring roles

| Role | Owns code in prod? | Owns customer outcome? | Primary output |
|---|---|---|---|
| Software engineer | Yes | No | Features in the core product |
| Solutions engineer / Sales engineer | Rarely (demos, POCs) | Pre-sale only | A won deal |
| Solutions architect | Designs, rarely builds | Partially | Architecture docs |
| Consultant | Sometimes | Yes, contractually | Deliverables, slides |
| **FDE** | **Yes** | **Yes, post-sale** | **Working system + metric + product feedback** |

## Compensation & logistics (check current data)

FDE pay is usually at or above SWE pay at the same company, because the role is scarce and travel-heavy. Use levels.fyi for live numbers. Many postings require travel to customer sites. For you, being in Ghana (GMT) is **UK/EMEA hours**, which is a real advantage for London and Europe-facing teams. Module 05 covers this.

## Exercise

Pull 10 current FDE / Applied AI / Forward Deployed postings. Paste them into `00-the-role/postings/` (one `.md` each). Then fill this table in `00-the-role/postings/SUMMARY.md`:

| Company | Flavour | Remote/onsite | Top 5 required skills | Skills I lack |
|---|---|---|---|---|

The "skills I lack" column, aggregated across all ten postings, should confirm (or correct) the gap analysis in module 01.
