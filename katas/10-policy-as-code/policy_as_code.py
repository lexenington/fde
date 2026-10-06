"""Kata 10: policy as code.

The customer's rules ("never approve more than GHS 50,000 without sign-off", "officers never see other
branches") must be enforced by code that the model cannot talk its way past. Write the check that runs on every
tool call the model proposes, before anything executes.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Call:
    tool: str
    args: dict


@dataclass(frozen=True)
class Ctx:
    user: str
    role: str                      # "officer", "finance" or "risk"
    branch: str | None = None
    approved: bool = False         # a human has signed off this specific call


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    needs_approval: bool = False


def check(call: Call, ctx: Ctx) -> Decision:
    """Decide whether `call` may run for `ctx`. Rules, in plain words:

    - Any tool not listed below is denied ("unknown tool"). Default deny.
    - `read_member` (args: member_id, member_branch): allowed if ctx.role is "risk" or ctx.branch equals
      member_branch. Otherwise denied.
    - `approve_invoice` (args: amount_ghs): only role "finance". An amount up to and including 50,000 is allowed.
      A larger amount sets needs_approval=True and is allowed only if ctx.approved is True. The amount must be a
      real number (int or float, not a bool or a string) and not negative; anything else is denied.
    - `send_whatsapp` (args: to): allowed only to numbers starting "+233".
    - `export_audit` (no args): only role "risk".
    - A call missing a required argument is denied ("missing ...").

    `reason` is a short sentence for the audit log in every case, allowed or not.
    """
    raise NotImplementedError
