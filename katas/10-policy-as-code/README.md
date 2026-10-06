# Kata 10: policy as code

**Time-box: 45 minutes.** Used in: 02/03 (injection, approval gates), the AWS track's *Prove* lab, Savanna's branch isolation, Lakeside's emergency rules.

**The task.** Implement `check` in `policy_as_code.py`. `python -m pytest -q katas/10-policy-as-code`.

**The principle.** A prompt that says "never approve over 50,000" is a request. This function is a rule. The model proposes a call; this code, which the model cannot edit or argue with, decides whether it runs. Every decision has a reason for the audit log.

**Watch for**
- default deny
- validation of the *types* of arguments: `True` is an `int` in Python, `float("nan")` compares false to everything, and `"1e9"` is a string a lazy `float()` will happily accept
- context comes from the **authenticated session**, never from the arguments the model supplied

**Then.** Write the three rules for Lakeside's bot that you'd enforce in code rather than in the prompt. Which of them can you only enforce *after* the model has answered?
