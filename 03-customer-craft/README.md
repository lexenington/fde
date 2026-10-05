# 03 — Customer craft

The technical modules make you a credible engineer. This module makes you an FDE. In interviews it's often the deciding factor: AI labs and startups run a dedicated "customer scenario" round, and strong engineers fail it all the time.

Your freelance years are a real foundation. The jump is from **"client tells me what to build"** to **"multiple stakeholders with conflicting goals, I find the real problem, define success as a number, and manage scope in writing."**

## The engagement lifecycle

```
 Discovery ──► Scoping ──► Build (weekly demos) ──► Production ──► Handover ──► Expansion
   1–2 wks      days         2–8 wks                  ongoing        1–2 wks       ...
   find the     success      show real progress       measure,       they own it   next use
   real         metric +     every week; renegotiate  support,                     case; product
   problem      SOW          scope in writing         harden                       feedback
```

## 1. Discovery: find the real problem

Customers usually arrive with a **solution** ("we want a chatbot"). Your job is to dig out the **problem** ("our support team can't keep up with 4,000 WhatsApp messages a day, 60% of which are order-status questions") and the **metric** ("first-response time from 6 hours to under 5 minutes").

**Rules for a discovery call**
- Talk ≤ 30% of the time.
- Ask for *the last time it happened*, not hypotheticals. "Walk me through the last invoice that went wrong."
- Ask to **see** the current workflow: screen share, spreadsheet, the actual WhatsApp group.
- Map stakeholders: who **pays** (economic buyer), who **uses** it, who can **block** it (IT, security, legal, works council), and who **champions** it.
- Before hanging up, agree on the next step with a date.

**Question bank:** see [templates/discovery-call.md](templates/discovery-call.md).

### Then redesign the process
Before you scope, map the current process step by step from a real recent case, and redesign it for agents: [templates/process-map.md](templates/process-map.md). AWS's FDE methodology calls this "Agentic Process Transformation": start from the business process, reimagine it, ship to production, prove the result ([AWS FDE track](../aws-fde-track/README.md)). The biggest wins usually come from removing steps that only exist to catch earlier errors, not from automating them.

## 2. Scoping: write it down

A one-page scoping doc, sent within 24 hours of discovery, signed off by the sponsor. It holds the problem, the success metric with a baseline, in-scope, **explicitly out-of-scope**, what you need from them (data access, people's time) with dates, risks and milestones. Template: [templates/scoping-doc.md](templates/scoping-doc.md).

> The out-of-scope list is the most valuable section. It's what you point at in week 5 when someone asks for "just one more thing."

## 3. Build: weekly demos, not big reveals

- Demo **real progress on their data** every week, even if it's ugly.
- Send a short written update every Friday: [templates/weekly-update.md](templates/weekly-update.md). Executives read these; they don't attend standups.
- When scope changes, use the line: *"Yes, we can do that. It means X moves to phase 2, or the date moves to Y. Which do you prefer?"* Make the trade-off theirs, and do it in writing.

## 4. Production & incidents

Things will break in front of the customer. What earns trust is how fast you tell them, how clearly you explain it, and whether it happens again. Template: [templates/incident-review.md](templates/incident-review.md). Blameless, specific, with action items that have owners and dates.

## 5. Handover & product feedback

The engagement isn't done until (a) their team can run it without you and (b) your product team has heard what you learned. Write the internal field note: [templates/field-feedback.md](templates/field-feedback.md). At AI labs this feedback loop is a formal part of the job.

## 6. The commercial side

FDEs aren't salespeople, but you work inside a deal and need to understand how it works.

- **How deals move:** proof of concept (2–4 weeks, often unpaid, one workflow) → paid pilot (one team, real users, a success metric written into the contract) → production rollout → expansion (more teams, more use cases). Most AI projects stall between pilot and production. Your job is to design the pilot so that "go to production" is the obvious next step: real data, real users, and a metric the buyer already cares about.
- **Business case:** sponsors need a number they can defend to their CFO. Learn to build a simple one: hours saved × loaded cost, errors avoided × cost per error, revenue protected, minus run cost (model tokens, infra, human review). Template: [templates/business-case.md](templates/business-case.md). Be conservative. An inflated ROI that misses destroys trust faster than a modest one that's met.
- **Unit economics of AI:** cost per completed task (not per API call) is what decides whether a use case survives at scale. Your eval harness already measures it. Put it in every report.
- **Contracts you'll see:** MSA, SOW, DPA (data processing agreement), order forms. You don't negotiate them, but you must know what the SOW commits *you* to deliver, and flag early when scope drifts beyond it.

## 7. Professional conduct with customer data

These are the mistakes that end engagements, and FDE careers, fastest:
- Customer data stays where the contract says it can be. Never paste it into personal tools, unapproved AI tools, or your own laptop's downloads folder "just to look".
- Use the least access you need, ask for it in writing, and give it back when you're done.
- Don't use one customer's data, code or story to help another without explicit permission. Anonymised case studies need sign-off too.
- If you see something you shouldn't (a security hole, exposed credentials, data you weren't meant to have), report it immediately to the customer and your own company. Don't quietly fix it, and don't quietly ignore it.

## Communication skills to drill

| Skill | Drill |
|---|---|
| **Explain to execs** | Record yourself explaining "why the AI sometimes gets invoices wrong and what we do about it" in 90 seconds, no jargon. Re-record until a non-technical friend can repeat it back |
| **Explain to engineers** | Whiteboard your RunMySales architecture in 5 minutes, including failure modes |
| **Say no** | Practise the scope-trade-off line above until it's automatic |
| **Bad news** | Write the email: "the go-live will slip 2 weeks because your IT team hasn't granted DB access." Firm on facts, no blame, clear ask |
| **Writing** | Every lab and engagement in this repo ends with a one-page report. Cut each one by 30% before you commit it |
| **Live demo** | Always have a recorded backup. Demo the *user's* workflow, not your features |

## Practice plan (runs in parallel with module 02)

- **Weekly:** One mock discovery call with a friend who runs a business, any business. Use the question bank. Produce a scoping doc within 24 h. Keep them in `03-customer-craft/practice/`.
- **Do this for real at least once:** find a Ghanaian SME (a pharmacy, a logistics firm, a school; your network from freelance work is perfect for this) and run actual discovery for an AI automation. That can become engagement #3 in module 04, and a genuine reference.

## Reading
- *The Mom Test*, Rob Fitzpatrick: discovery without leading questions (short, read it first)
- *The Trusted Advisor*, Maister, Green & Galford
- *Never Split the Difference*, Chris Voss: chapters on labelling and calibrated questions
- *The Pyramid Principle*, Barbara Minto: answer first, then support. This is how you write to execs
