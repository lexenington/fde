import pytest

from policy_as_code import Call, Ctx, Decision, check

OFFICER = Ctx("ruth", "officer", branch="TAMALE-C")
FINANCE = Ctx("yaw", "finance")
RISK = Ctx("esi", "risk")


def d(tool, ctx, **args):
    return check(Call(tool, args), ctx)


def test_unknown_tools_are_denied_by_default():
    r = d("delete_everything", RISK)
    assert r.allowed is False and "unknown" in r.reason.lower()


def test_decisions_always_explain_themselves():
    for r in (d("read_member", OFFICER, member_id="M1", member_branch="TAMALE-C"), d("export_audit", OFFICER)):
        assert isinstance(r, Decision) and r.reason.strip()


@pytest.mark.parametrize("ctx,member_branch,allowed", [
    (OFFICER, "TAMALE-C", True), (OFFICER, "BOLGA", False), (RISK, "BOLGA", True),
    (Ctx("x", "officer", branch=None), "BOLGA", False), (FINANCE, "TAMALE-C", False),
])
def test_read_member_is_scoped_to_the_branch(ctx, member_branch, allowed):
    assert d("read_member", ctx, member_id="M1", member_branch=member_branch).allowed is allowed


@pytest.mark.parametrize("amount,approved,allowed,needs", [
    (100, False, True, False), (50_000, False, True, False), (50_000.0, False, True, False), (0, False, True, False),
    (50_000.01, False, False, True), (250_000, False, False, True), (250_000, True, True, True),
])
def test_invoice_approval_thresholds(amount, approved, allowed, needs):
    r = d("approve_invoice", Ctx("yaw", "finance", approved=approved), amount_ghs=amount)
    assert (r.allowed, r.needs_approval) == (allowed, needs)


@pytest.mark.parametrize("ctx", [OFFICER, RISK])
def test_only_finance_may_approve_invoices_even_with_a_sign_off(ctx):
    assert d("approve_invoice", Ctx(ctx.user, ctx.role, branch=ctx.branch, approved=True), amount_ghs=10).allowed is False


@pytest.mark.parametrize("bad", [-5, "100", "1e9", None, True, [100], float("nan")])
def test_amounts_must_be_real_non_negative_numbers(bad):
    assert d("approve_invoice", FINANCE, amount_ghs=bad).allowed is False


@pytest.mark.parametrize("to,allowed", [("+233244123456", True), ("+2348031234567", False), ("0244123456", False), ("", False)])
def test_whatsapp_only_goes_to_ghana(to, allowed):
    assert d("send_whatsapp", OFFICER, to=to).allowed is allowed


def test_only_risk_exports_the_audit_log():
    assert d("export_audit", RISK).allowed is True
    assert d("export_audit", OFFICER).allowed is False
    assert d("export_audit", FINANCE).allowed is False


@pytest.mark.parametrize("tool,ctx,args", [
    ("read_member", OFFICER, {"member_id": "M1"}), ("read_member", OFFICER, {"member_branch": "TAMALE-C"}),
    ("approve_invoice", FINANCE, {}), ("send_whatsapp", OFFICER, {}),
])
def test_missing_arguments_are_denied(tool, ctx, args):
    r = d(tool, ctx, **args)
    assert r.allowed is False and "missing" in r.reason.lower()


def test_extra_arguments_never_grant_anything():
    """A model can put anything in args. 'role': 'risk' in the arguments must change nothing."""
    assert d("export_audit", OFFICER, role="risk", approved=True).allowed is False
    assert d("read_member", OFFICER, member_id="M1", member_branch="BOLGA", ctx_branch="BOLGA").allowed is False
