# Interview question bank

Answer out loud, timed, and record yourself. Write your best answers in `05-getting-hired/answers/`.

## Decomposition / customer case (the round that decides FDE loops)

**Framework (spend the first 5 minutes here, not on solutions):**
1. **Clarify the goal.** What business outcome? Measured how? Baseline?
2. **Users & stakeholders.** Who uses it, who pays, who can block it?
3. **Current workflow.** What happens today, step by step? Where's the pain?
4. **Data & systems.** What exists, where, what quality, who owns access?
5. **Constraints.** Security, compliance, timeline, budget, skills of the team who'll run it.
6. **MVP.** The smallest thing that proves value in ~2 weeks. Say what you're *not* doing.
7. **Success & risks.** How you'll measure, what could go wrong, how you'd find out.
8. **Phase 2+.** Where it goes if the MVP works.

**Practice prompts**
1. A national bank wants "an AI for the call centre." Go.
2. A hospital network says doctors spend 2 hours a day on notes. They want to fix it in 8 weeks.
3. A shipping company's customs paperwork causes containers to sit at Tema port for days. They have ~20 document types.
4. A retailer's demand forecasts are wrong and stores keep running out of stock. They have 5 years of POS data in three different systems.
5. A government agency wants citizens to be able to ask questions about benefits in 5 local languages.
6. Your agent is live at a customer and their exec forwards a screenshot where it gave a wrong refund amount. Walk through the next 48 hours.
7. The customer wants feature X. Your product team says X is 6 months away. The deal renewal is in 6 weeks.
8. Halfway through an engagement you discover the success metric everyone agreed on can't be measured with the data available.
9. Two senior stakeholders at the customer want contradictory things and both say they're the decision-maker.
10. A customer's security team blocks outbound traffic to all LLM APIs. The project is due in 4 weeks.

## Practical coding (45–60 min, real-world flavour)
1. Given a CSV of transactions with mixed date formats and currencies, produce daily totals in GHS; handle and report bad rows.
2. Write a client for a paginated, rate-limited REST API (respects `Retry-After`, resumes from a cursor after a crash).
3. Implement a webhook endpoint with HMAC verification, replay protection and idempotent processing.
4. Dedupe a list of customer records with fuzzy names and multiple phone formats; explain your threshold choice.
5. Build a minimal tool-using agent loop: two tools, a max-iteration guard, and an approval step before any write.
6. Given 20 LLM outputs and expected answers, write a grader and report accuracy by category.
7. Add caching and retries to a slow, flaky internal service call without changing its interface.

## System design (customer constraints first)
1. Design a document-processing pipeline for 50k docs/day with human review, deployable in the customer's VPC.
2. Design a permission-aware RAG system over SharePoint for a 10k-employee company.
3. Design a WhatsApp support agent for a telco with 5M customers, including escalation to 300 human agents.
4. Design the multi-tenant vs. single-tenant deployment model for an AI product selling to banks.
5. Design observability for an LLM agent so that the *customer's* ops team can debug it.

## AI-specific
1. When would you *not* use an agent? Give an example from your own work.
2. How do you build an eval set when the customer has no labelled data?
3. How would you validate an LLM-as-judge?
4. Explain indirect prompt injection and three mitigations, and which one you'd trust most.
5. Your accuracy went from 92% to 94% after a prompt change. Is that real? How do you know?
6. Cost per conversation is 3× what the customer budgeted. What levers do you pull, in what order?
7. RAG vs. putting the whole corpus in a long context window: how do you decide?
8. How did you decide when RunMySales should escalate to a human? How would you measure whether that rule is right?

## Behavioural: prepare 8 STAR stories
| # | Theme | Your candidate story |
|---|---|---|
| 1 | Requirements were wrong / the client asked for the wrong thing | (Verisage or freelance) |
| 2 | Shipped under a hard constraint | EatryCloud offline-first |
| 3 | Production broke in front of a customer | |
| 4 | Said no / renegotiated scope | |
| 5 | Learned a new domain fast | Restaurant ops? Sales? |
| 6 | Disagreement with a stakeholder | |
| 7 | Failure and what you changed | |
| 8 | Made a product better from field feedback | RunMySales escalation design |

**"Why FDE and not SWE?"** Draft: *"I'm at my best when I can see the person whose problem I'm solving. Building EatryCloud meant standing in restaurant kitchens watching orders get lost when the internet dropped. That's where I figured out what to build. FDE is that, as a job."*
