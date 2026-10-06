import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Call:
    tool: str
    args: dict


@dataclass(frozen=True)
class Ctx:
    user: str
    role: str
    branch: str | None = None
    approved: bool = False


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    needs_approval: bool = False


def _deny(reason, needs=False):
    return Decision(False, reason, needs)


def check(call, ctx):
    t, a = call.tool, call.args
    if t == "read_member":
        for k in ("member_id", "member_branch"):
            if k not in a:
                return _deny(f"missing argument {k}")
        if ctx.role == "risk" or (ctx.branch is not None and ctx.branch == a["member_branch"]):
            return Decision(True, "member is in the caller's branch or the caller is Risk")
        return _deny("member belongs to another branch")
    if t == "approve_invoice":
        if ctx.role != "finance":
            return _deny("only finance may approve invoices")
        if "amount_ghs" not in a:
            return _deny("missing argument amount_ghs")
        amt = a["amount_ghs"]
        if isinstance(amt, bool) or not isinstance(amt, (int, float)) or not math.isfinite(amt) or amt < 0:
            return _deny("amount must be a non-negative number")
        if amt <= 50_000:
            return Decision(True, "within the limit")
        if ctx.approved:
            return Decision(True, "above the limit, signed off", True)
        return _deny("above GHS 50,000 needs sign-off", True)
    if t == "send_whatsapp":
        if "to" not in a:
            return _deny("missing argument to")
        if isinstance(a["to"], str) and a["to"].startswith("+233"):
            return Decision(True, "Ghana number")
        return _deny("messages may only go to +233 numbers")
    if t == "export_audit":
        return Decision(True, "Risk may export") if ctx.role == "risk" else _deny("only Risk may export the audit log")
    return _deny("unknown tool")
