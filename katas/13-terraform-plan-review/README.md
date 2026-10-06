# Kata 13: review a Terraform plan

**Time-box: 45 minutes.** Used in: 02/04 (deploying into the customer's account, "private subnets only, no public IP"), the cross-account role you write for their security team.

**The task.** Implement `review` in `plan_review.py`. `python -m pytest -q katas/13-terraform-plan-review`.

**Why.** The customer's platform team reads your `terraform plan` as a review artifact before the Thursday change board. Finding your own public IP, open port or unencrypted disk first is what makes you the engineer they trust with a role in their account. This is a tiny version of what policy tools (OPA/Conftest, tfsec, Checkov) do.

**Ghana context.** Data-protection obligations (the Data Protection Act, 2012, and the Commission's registration requirements) are why customers ask "where does the data live and who can reach it" before anything else. A public database or an unencrypted volume is not only a security finding, it is an answer you can't give them.

**Think about**
- missing means *unsafe*, not "fine": an absent `storage_encrypted` is not `true`
- a plan lists deletions too; flagging something Terraform is about to destroy is noise
- port ranges are ranges

**Then.** Run `terraform show -json` on your 02/04 lab and pipe it through your `review`. What does it find that you hadn't intended?
