# Kata 8: what was the rule on this date?

**Time-box: 30 minutes.** Used in: Savanna (policy answers "as of" a date, circulars that supersede each other, one not yet in force).

**The task.** Implement `value_as_of` and `upcoming` in `rule_as_of.py`. `python -m pytest -q katas/08-rule-as-of`.

**Think about**
- the question is about *time*, not about which document is newest or which was retrieved first
- the effective date is inclusive, and an amendment isn't "upcoming" on the day it takes effect
- a falsy value (0, "") is still a value
- real corpora need this logic *before* retrieval: your RAG should be handed the right text, and the model shouldn't be trusted to work out dates

**Why it is a regulated-finance problem.** When Bank of Ghana or an auditor asks "what was the rule on 14 March, and who told the loan officers?", "the newest PDF" is the wrong answer and "we don't know" is worse. Dated, citable rules are how Esi's team defends a decision after the fact.

**Then.** In your Savanna copilot, where does `as_of` enter the pipeline? Retrieval filter, prompt, or post-check? What would break if it only lived in the prompt?
