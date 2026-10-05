# AWS FDE track

AWS has its own Forward Deployed Engineering organisation, backed by a reported $1B investment to embed engineers with customers to build agentic AI. In 2026 it extended the model to consulting partners, with **FDE pathways and credentials on AWS Skill Builder**. This track maps that programme onto this curriculum, adds what it emphasises that we didn't, and gives you a route to the credentials.

## What the AWS programme actually is (as of Oct 2026, check Skill Builder for current rules)

**It's not a public certification.** The FDE pathways and credentials are for **AWS Partner** organisations: free on Skill Builder for partner staff, and validated through hands-on work, not just course completion.

### Three pathways, each answering one production question

| Pathway | Focus (AWS's wording) | Production question | Where this curriculum covers it |
|---|---|---|---|
| **Ground** | Trusted enterprise data, systems, domain ontologies, business context | Does the system understand the business and use reliable information? | 02/01 messy data, 02/02 integration, **+ ontology lab below** |
| **Orchestrate** | Dependable agents, tools, workflows, identity, recovery | Can the system perform real work reliably? | 02/03 agents & MCP, 02/02 identity, **+ agent identity & recovery lab below** |
| **Prove** | Evaluation, observability, security, policy, human control | Can the customer trust it in production? | 02/03 evals & human-in-the-loop, 02/04 observability, 03 conduct |

### Credentials
| Credential | Requires |
|---|---|
| **FDE Validated** | An active AWS **Associate- or Professional-level** certification + all required validation activities in **at least one** pathway + a points total across all three |
| **FDE Advanced** | An active **AWS Certified Generative AI Developer – Professional (AIP-C01)** + the published requirements across **all three** pathways |

Validation activities include assessments, SimuLearn (simulated customer scenarios), microcredentials and hands-on labs in AWS-provisioned environments.

### The methodology: "Agentic Process Transformation"
1. Start from the **business process**, not the technology.
2. **Reimagine** the process for agents. Don't just bolt AI onto the old steps.
3. **Deploy to production** in weeks.
4. **Demonstrate measurable results.**

Partner engineers must pass "an AWS-defined technical bar" before engaging any customer. AWS frames this as a production-engineering standard, not a certification checkbox, which matches the philosophy of this repo.

## Your route

You aren't at an AWS partner, so the pathways aren't open to you directly. Two moves get you there:

1. **Take AIP-C01 (Generative AI Developer – Professional).** It's open to anyone, it's the prerequisite for FDE Advanced, and its domains map almost one to one onto this curriculum (table below). It also replaces the earlier suggestion of Solutions Architect – Associate as your next certification: one Professional-level AI certification beats an Associate one for FDE work.
2. **Target AWS partners building FDE practices** (tier D in [05](../05-getting-hired/README.md)). They need credentialed engineers and will put you through the pathways. "AIP-C01 + three published case studies" is a strong application to exactly these firms. Several already sell FDE-as-a-service on AWS Marketplace; search it for "Forward Deployed Engineer" to build your target list.

Longer term, if Webfront360 becomes a services firm ([06](../06-beyond/README.md), direction 4), becoming an AWS Partner with its own FDE practice is a real option.

### AIP-C01 domains → modules

| Exam domain | Weight | Where in this repo |
|---|---|---|
| 1. Foundation model integration, data management & compliance | 31% | 02/01, 02/03 (RAG, structured outputs), 02/04 (in-boundary models), Ghana DPA in 02/02 |
| 2. Implementation & integration (incl. agentic AI, tool integrations, MCP) | 26% | 02/02, 02/03 (agents, MCP), Orchestrate lab below |
| 3. AI safety, security & governance | 20% | 02/03 (injection, guardrails), 02/02 SECURITY.md, 03 conduct |
| 4. Operational efficiency & optimisation | 12% | 02/03 cost & caching, 02/04 |
| 5. Testing, validation & troubleshooting | 11% | 02/03 eval harness |

**What the exam adds that this repo doesn't teach:** the AWS-specific services. Learn these hands-on through the AWS-flavoured labs below, not by memorising:
- **Amazon Bedrock:** model access, Knowledge Bases (managed RAG), Guardrails, model evaluation.
- **Amazon Bedrock AgentCore:** managed runtime, memory, gateway (turns APIs into agent tools, MCP-compatible), identity and observability for agents.
- **Strands Agents:** AWS's open-source agent SDK.
- **Supporting services:** vector stores (OpenSearch Serverless, pgvector on Aurora), Step Functions for workflows, Lambda, EventBridge, CloudWatch.

Check the current exam guide on docs.aws.amazon.com; the service list changes.

## Lab additions (inspired by the pathways)

### Ground: build a domain ontology (extends 02/01)
Data alone isn't enough; agents need to understand what the data *means* to the business.
1. For Kumasi Fresh Foods, write `ontology.md`: the core entities (Customer, Account, Delivery, Order, Payment, Route), their relationships, their identifiers in each source system, and the **business rules** ("a customer with balance < −GHS 500 can't receive new deliveries", "MoMo and bank payments reconcile differently").
2. Encode it as something machine-usable: Postgres tables with constraints, or a small graph (nodes + edges in JSON, or Neo4j if you want to learn it).
3. Give an agent the ontology as context and ask it 20 business questions ("can we deliver to Ama in Tamale tomorrow?"). Compare accuracy **with vs. without** the ontology in your eval harness. That delta is the whole argument for grounding.

### Orchestrate: agent identity and recovery (extends 02/03 + 02/02)
1. **Identity:** your agent acts *on behalf of a user*. Make every tool call carry that user's identity and permissions (a scoped token passed through to the tool, never a shared admin key). Test: a sales rep's agent can't read a manager-only record even when asked to.
2. **Recovery:** make a multi-step agent workflow survive failure. Kill the process mid-run (after it has booked the appointment but before it has updated the CRM). On restart it must resume, not repeat the booking. Use checkpointing + idempotency keys, and a compensating action for steps that can't be retried.
3. **Human control:** add an approval gate before any irreversible write, with a timeout and an escalation path.

### Prove: policy as code (extends 02/03)
Write the customer's rules ("never approve invoices over GHS 50,000 without review", "never send member data outside branch") as **code-enforced policies** checked outside the model, not as prompt instructions. Show in the eval that a jailbreak attempt that fools the prompt still can't break the policy.

### AWS-flavoured variants (do one when preparing for AIP-C01)
- Rebuild the invoice extractor on **Bedrock** (Claude via Bedrock) with **Guardrails**, and run your same eval harness against it. Did the quality numbers change?
- Deploy the RunMySales-style agent on **AgentCore** with Strands Agents. Expose your CRM sync as a tool through AgentCore Gateway, and wire up its identity and observability.
- Replace your own RAG in engagement 2 with **Bedrock Knowledge Bases** and compare retrieval quality on your eval set. Be ready to explain to a customer when managed beats custom.

## The methodology in your own work

Add a **process-redesign step** to every engagement before scoping: map the current process ([template](../03-customer-craft/templates/process-map.md)), then redesign it for agents. The biggest wins usually come from removing steps entirely, not from speeding them up.

## Sources
- [Introducing Forward Deployed Engineering for Partners](https://aws.amazon.com/blogs/apn/introducing-forward-deployed-engineering-for-partners-winning-the-future-of-enterprise-ai/)
- [New FDE Pathways for AWS Partners](https://aws.amazon.com/blogs/apn/new-fde-pathways-for-aws-partners-get-ready-for-production-agentic-ai-delivery/)
- [AIP-C01 exam guide](https://docs.aws.amazon.com/aws-certification/latest/ai-professional-01/ai-professional-01.html)
