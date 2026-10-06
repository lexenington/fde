# Engagement 2 — Savanna Microfinance

## Brief
Savanna Microfinance has 22 branches across the Northern, Upper East and Bono regions and ~60,000 members. Loan officers spend ~40% of their day looking things up: credit policy (a 140-page PDF, amended by circulars), member repayment history (a core-banking export), and group-lending rules. Wrong answers cause policy breaches that the regulator flags.

## Stakeholder memos
- **COO (sponsor):** "A copilot so officers get policy answers and member summaries in seconds. Measure: time per loan application."
- **Head of Risk & Compliance:** "Every answer must cite the policy section. Officers must never see members outside their branch. I need an audit trail I can hand to the Bank of Ghana."
- **CIO:** "We're on AWS. Data must stay in our account; we'd prefer af-south-1. We use Microsoft Entra ID for staff login. No new long-lived credentials."
- **Senior loan officer:** "Half the 'policy' is in WhatsApp messages from the regional manager. And member names are spelled five different ways between core banking and the field sheets."

## Constraints
- Member data comes from three sources that disagree (use the techniques from 02/01).
- Policy corpus: base PDF + dated circulars that **supersede** sections. The copilot must answer with the *current* rule and cite it.
- Branch-level row security enforced in retrieval *and* in SQL, not in the prompt.
- Deploy into a customer AWS account via Terraform (02/04), SSO via Entra ID (02/02), Claude accessed inside the customer's cloud boundary (Bedrock) or via an allow-listed egress, as decided in scoping.

## Acceptance bar
- Eval: ≥ 80 policy questions with gold answers + gold citations, including questions where a circular overrides the base policy. Report answer accuracy, citation accuracy, and abstention rate ("I don't know, ask Risk") on questions the docs don't answer.
- Permission tests: an officer from branch A cannot retrieve, or be told about, members of branch B, including via indirect questions and prompt injection.
- Member-summary accuracy measured against a hand-built truth set of 30 members.
- Audit log: every question, retrieved chunk, answer and user, exportable as CSV for Risk.
- Teardown → redeploy from zero in < 45 min.

## What a strong submission includes
- A memo to the Head of Risk explaining, in plain language, how the system can be wrong and what controls exist.
- An AI governance pack for Risk & Compliance: intended use and prohibited uses (e.g. the copilot never makes or recommends a credit decision), human oversight points, how answer quality is monitored after go-live, the incident process when it gives a wrong policy answer, and a check of member summaries for unfair differences by region or gender. Written so Risk could hand it to the Bank of Ghana.
- A decision record: Bedrock vs. first-party API vs. egress proxy, with trade-offs.
- Field feedback on what a "regulated financial services" deployment kit should contain.
