# My AI engineering opinions

Employers hiring FDEs want someone with "opinions based on experience and actually deploying these", not a list of buzzwords. This page is where those opinions live. **Each opinion must point to evidence from your own work**: a saved run in `lab/runs/`, a `CHANGELOG.md` entry, an engagement eval, a RunMySales incident. If you can't link evidence, write "untested" and go and test it, or mark it as borrowed and name the source.

Keep it short and keep it current. When a run contradicts an opinion, change the opinion, and keep the old one struck through with the date. Being shown wrong by your own eval is good interview material.

## Format

> **Opinion:** one sentence you'd say to a CTO.
> **Evidence:** link + the number.
> **When I'd do the opposite:** the conditions that flip it.

## Prompts to fill (add your own)

**Architecture**
- When I'd use a single call, a code-orchestrated workflow, an agent, or no LLM at all
- Router vs. orchestrator-worker vs. one agent with more tools: when each one has paid off for me
- Multi-agent: the one case where I'd use it, and what it cost in tokens and eval difficulty
- Frameworks (LangGraph, Strands, the Claude Agent SDK, CrewAI…) vs. a hand-rolled tool loop: what a framework would buy me on a customer engagement, and what it would cost the customer's team to maintain
- Where human-in-the-loop belongs, and how I'd set the threshold

**Model configuration**
- Model choice per step: which steps get the strongest model, and which get the cheapest one, by eval result
- Sampling settings (temperature and friends): what I set for extraction vs. conversation, and whether it measurably changed anything. Check the current API docs first, since not every model accepts every parameter
- Effort / thinking budget: where it moved accuracy, and where it only added latency and cost
- Prompt caching: the saving I measured, and when it didn't help

**Retrieval**
- Chunk size and overlap: what I tried and what the retrieval metric did
- Hybrid search and reranking: whether they earned their latency on my data
- RAG vs. long context: the corpus size and question type where I'd switch

**Evals and safety**
- Code graders vs. LLM-as-judge: when I trust a judge, and the agreement number that made me trust it
- How many golden cases are enough before I believe a 2-point improvement
- The prompt-injection defence I'd trust most, and the one I'd never rely on alone
- Agents handing work to agents: what I'd never let one agent pass to another without a check in code (identity, permissions, money, writes)

**Voice and languages**
- Speech-to-text choice for Twi and code-switched speech, by word error rate on my own clips
- The latency target I'd commit to for a phone agent, and what it took to meet it

## Opinions

<!-- Start here. Aim for 10 with evidence by the end of week 7, and 20 by the end of the engagements. -->
