# 02/03 — AI engineering & evals

**Prove it (skip if yes):** For an LLM feature you've shipped (RunMySales counts), can you tell me, *with a number from a reproducible run*: its accuracy on the cases the business cares about, how that changed after your last prompt edit, its cost per conversation, its p95 latency, and what happens when a user tries prompt injection?

You've already built agents, which puts you ahead of most applicants. This module is about getting from **"it works in the demo"** to **"the customer's risk team signed off and it's been live for 90 days."**

## The production LLM stack, as an FDE sees it

```
 customer problem ──► task decomposition ──► simplest architecture that works
                                               │  single call → workflow → agent
                                               ▼
                  context: retrieval / tools / customer data (permissions!)
                                               ▼
                  guardrails: input checks, structured output, validation, PII
                                               ▼
                  human-in-the-loop: confidence routing, review queues, escalation
                                               ▼
        EVALS ◄──── observability: traces, cost, latency, feedback, drift ────► iterate
```

Evals sit at the centre. Every other box gets changed *because an eval said so*.

## Concepts to learn

| Topic | What "good" looks like |
|---|---|
| **Architecture choice** | Start with one call. Move to a code-orchestrated workflow when steps are known. Use an agent only when the path is genuinely open-ended. Be able to justify the choice in cost, latency and failure-mode terms. Read Anthropic's "Building effective agents" |
| **Prompting for production** | System prompts as specs: role, context, rules, output contract, examples of edge cases. Version them like code |
| **Prompt versioning & management** | Prompts live in files with an ID and version, not inline strings. Every eval run records which prompt version (and model) produced it, so "why did behaviour change on Tuesday?" has an answer. Know how to roll back, and know when a registry tool (Langfuse prompts, PromptLayer, or a plain `prompts/` folder + git tags) is worth it. Part of the handover: the customer's team must be able to change a prompt *and* see the eval delta |
| **Structured outputs** | Schema-constrained JSON (`client.messages.parse` + Pydantic), strict tool schemas, then *business* validation on top (totals add up, dates plausible) |
| **Tool use / agents** | Tool design (few, well-described, idempotent), permission checks *inside* tools, approval gates for writes, max-iteration and budget limits |
| **Memory & state** | Short-term memory is the context window; long-term memory is your database or vector store. Decide what the agent must remember across steps, sessions and users, where it lives, who can read it (memory is a data-leak surface), and when it expires. Compaction/summarisation for long tasks; durable workflow state so a crash resumes instead of restarting or double-writing |
| **Multi-agent systems** | Orchestrator-worker, parallel sub-agents, handoffs. Mostly you should be able to explain *why not*: more tokens, harder evals, new failure modes between agents. Use it when subtasks are genuinely independent or one context can't hold the job. Customers will ask, because vendors pitch it |
| **Retrieval (RAG)** | Chunking, hybrid search (BM25 + embeddings), reranking, citations, permission-aware retrieval (user only retrieves docs they can see), when long context beats RAG |
| **Evals** | Golden sets from real data, code-based graders first, LLM-as-judge with a rubric second (and validate the judge against human labels), regression runs on every change, slice metrics (by customer segment, doc type, language) |
| **Human-in-the-loop** | Confidence/abstention, review queues, measuring auto-resolution rate vs error rate. The trade-off curve is what the customer actually buys |
| **Safety & security** | Prompt injection (direct and indirect, i.e. via documents and tool results), data exfiltration via tools, PII redaction, output filtering, refusal handling (`stop_reason == "refusal"`) |
| **AI governance** | The policies and controls a customer needs *before* they let AI near production: acceptable-use policy, model risk assessment, human oversight points, bias/fairness monitoring on outputs that affect people (e.g. loan decisions), incident process, and an audit trail. Know the reference frameworks by name and what each asks for: NIST AI RMF, ISO/IEC 42001, the EU AI Act risk tiers (matters for any customer selling into Europe). In Ghana, check what the Data Protection Commission, Bank of Ghana and the national AI strategy currently say, since this is moving |
| **Cost & latency** | Prompt caching, model choice per step, effort levels, batching for offline work, streaming for UX, measuring cost per *completed task* not per call |
| **Observability** | Traces per request (inputs, outputs, tool calls, tokens, latency), feedback capture, drift alerts. Know one LLM tracing tool (Langfuse, Arize Phoenix, or OpenTelemetry's GenAI conventions) |
| **MCP (Model Context Protocol)** | The standard way to plug a customer's systems into Claude and other AI clients. Build MCP servers (tools, resources, prompts), handle auth (OAuth for remote servers), and scope permissions. A large share of FDE integration work is now "write an MCP server for their system" |
| **Agent platforms** | Know when to hand-roll the tool loop, use the SDK's tool runner, use the Claude Agent SDK (Claude Code as a library, good for agents that read and write files), or use hosted Managed Agents. Customers will ask which one, and why |
| **Voice & languages** | Speech-to-text and text-to-speech pipelines, latency budgets for voice agents, and **evaluating quality in Twi, Ga, Ewe, Hausa and code-switched speech**, where models are weakest. Build language-specific eval slices; never assume English accuracy carries over |
| **Using coding agents on the job** | FDEs ship fast in unfamiliar codebases with Claude Code and similar tools. Learn to direct them well, review their output critically, and respect each customer's rules on which tools may see their code and data |

## Lab: invoice extraction with an eval harness

A (fictional) Ghanaian FMCG distributor receives ~3,000 supplier invoices a month as scanned PDFs, emails and WhatsApp photos. Finance re-keys them by hand. They want automation, but the CFO's condition is: **"I need to know how often it's wrong, and anything it's unsure about goes to a human."**

```
lab/
  schema.py         # the output contract (Pydantic)
  extract.py        # one function: document text -> Invoice
  eval.py           # runs the golden set, scores per field, cost, latency, review routing; diffs vs last run
  data/docs/*.txt   # 10 OCR'd invoices, some deliberately nasty
  data/gold.json    # expected values + which docs MUST be routed to review
  runs/             # every eval run is saved here; compare runs, never vibes
```

```powershell
cd 02-technical-depth/03-ai-engineering/lab
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python eval.py            # baseline run
python eval.py --only inv_07   # debug a single doc
```

### Your tasks, in order

1. **Baseline.** Run it. Read every failure. Write down *why* each one failed. Don't fix anything yet.
2. **Expand the golden set to 30+ docs.** Write 20 more, modelled on real invoice weirdness: handwritten corrections, two currencies, credit notes (negative totals), VAT/NHIL/GETFund levies (Ghana-specific!), multi-page, a receipt that isn't an invoice. Your eval is only as good as its hardest cases.
3. **Improve extraction** via prompt, schema or business-rule validation (e.g. `subtotal + taxes ≈ total`, otherwise route to review). Re-run after each change. Keep a `CHANGELOG.md`: change → metric delta.
4. **Tune the review threshold.** `eval.py` prints a routing table: for each confidence threshold, the % auto-processed, the error rate on those, and how many must-review docs leaked through. Is the model's self-reported `confidence` actually calibrated? Try replacing or combining it with business-rule checks and compare the tables. Then pick a threshold and justify it in money: cost of a wrong auto-posted invoice vs. cost of a human review. This table is what you'd put in front of the CFO.
5. **Red-team.** `inv_09` contains an indirect prompt injection. Make sure it can't change totals or skip review. Add 3 more injection variants.
6. **Cost.** Report cost per 1,000 invoices from the run data. Try prompt caching on the system prompt and a cheaper model for easy docs. Was the quality trade-off worth it? Show the numbers.
7. **Write `REPORT.md` for the CFO.** One page, no jargon: accuracy, what goes to humans, expected monthly savings, risks, what you need from them (e.g. 200 real invoices with correct values).

Run `python -m pytest -q` before trusting any number: `test_eval.py` tests the grader itself. If you change the scoring, add a test first.

### Stretch
- **Wrap it as an MCP server** (`extract_invoice`, `list_review_queue`, `approve_invoice` tools) and connect it to Claude Desktop or Claude Code. Notice what you have to decide about permissions: should the AI client be allowed to *approve*?
- **Version the prompt.** Move the system prompt out of `extract.py` into a versioned file, and make every saved run record the prompt version and model. Then roll back to an older version and show the eval delta. Question to answer in `CHANGELOG.md`: could the customer's team do this without you?
- **Governance pack** for the CFO's risk/audit people: one page covering intended use, what the system must never do, where humans sign off, how errors are detected and reported, and which fields are logged for audit. Map each item to the relevant NIST AI RMF function (Govern / Map / Measure / Manage).
- Add an LLM-as-judge grader for a free-text field (e.g. `line_items` descriptions). Validate the judge: grade 20 by hand and report agreement.
- Turn it into a service: FastAPI endpoint + review-queue UI (your Next.js skills) + a trace per request.
- Port the same harness to RunMySales conversations: build 50 scripted conversations and grade "booked correctly", "escalated when it should", "never promised a discount it can't give".
