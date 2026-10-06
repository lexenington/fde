"""Lab 02/04 reviewer: reads what you produced and reviews it the way Adom's platform team would.

* `lab/infra/plan.json` (`terraform plan -out=plan.out && terraform show -json plan.out > plan.json`): findings for
  public exposure, plus the components the brief requires.
* The teardown drill: start a timer, destroy, rebuild, stop. The 30 minute bar is checked, and every drill is kept.
* RUNBOOK.md and HANDOVER.md: the sections the brief asks for are there (it does not judge whether they are any good).

Nothing here talks to AWS. It reads files, so it works offline and costs nothing.
"""

import json
import re
import time
from datetime import datetime, timezone

from . import config

LAB = "04-deploy-anywhere"
BAR_MINUTES = 30
OPEN = ("0.0.0.0/0", "::/0")


def lab_dir():
    return config.LABS_DIR / LAB / "lab"


def _actions(rc):
    ch = rc.get("change") or {}
    return ch.get("after"), set(ch.get("actions") or [])


def _is_world(cidrs):
    return any(c in OPEN for c in cidrs or [])


def _containers(after):
    try:
        return json.loads(after.get("container_definitions") or "[]")
    except (json.JSONDecodeError, TypeError):
        return []


SECRET_NAME = re.compile(r"(pass(word)?|secret|token|api[_-]?key|private[_-]?key)", re.I)


def review_plan(plan):
    """Return (findings, present): findings are things to fix; present says which required components the plan creates."""
    out, counts = [], {}
    for rc in plan.get("resource_changes") or []:
        after, actions = _actions(rc)
        if after is None or not ({"create", "update"} & actions):
            continue
        addr, typ = rc["address"], rc["type"]
        counts[typ] = counts.get(typ, 0) + 1

        def bad(rule, why, fix):
            out.append({"address": addr, "rule": rule, "why": why, "fix": fix})

        if typ == "aws_instance" and after.get("associate_public_ip_address") is True:
            bad("public-ip", "The brief says no public IP on compute.", "Remove associate_public_ip_address, run in a private subnet.")
        if typ == "aws_subnet" and after.get("map_public_ip_on_launch") is True:
            bad("public-subnet", "Anything launched here gets a public IP.", "Set map_public_ip_on_launch = false. Compute belongs in private subnets only.")
        if typ == "aws_lb" and after.get("internal") is not True:
            bad("public-alb", "The ALB faces the internet. The brief says internal.", "internal = true; users arrive over VPN or PrivateLink.")
        if typ == "aws_ecs_service":
            nc = (after.get("network_configuration") or [{}])
            nc = nc[0] if isinstance(nc, list) and nc else (nc if isinstance(nc, dict) else {})
            if nc.get("assign_public_ip") is True:
                bad("public-ip", "The task gets a public IP.", "assign_public_ip = false")
        if typ == "aws_security_group":
            for r in after.get("ingress") or []:
                if (_is_world(r.get("cidr_blocks")) or _is_world(r.get("ipv6_cidr_blocks"))):
                    bad("open-ingress", f"Ingress open to the world on {r.get('from_port')}-{r.get('to_port')}.", "Restrict to the customer's VPN or the ALB's security group.")
                    break
            for r in after.get("egress") or []:
                if (_is_world(r.get("cidr_blocks"))) and not (r.get("from_port") == 443 and r.get("to_port") == 443):
                    bad("open-egress", "Egress to anywhere on anything. The brief says only api.anthropic.com (or Bedrock via an endpoint).", "Egress 443 only, and through a proxy or NAT with a domain allow-list.")
                    break
        if typ in ("aws_vpc_security_group_ingress_rule", "aws_security_group_rule"):
            ing = typ == "aws_vpc_security_group_ingress_rule" or after.get("type") == "ingress"
            cidr = [after.get("cidr_ipv4"), after.get("cidr_ipv6")] + list(after.get("cidr_blocks") or [])
            if ing and _is_world(cidr):
                bad("open-ingress", "Ingress open to the world.", "Restrict the source.")
        if typ == "aws_db_instance":
            if after.get("storage_encrypted") is not True:
                bad("unencrypted-storage", "RDS storage is not encrypted, or the plan doesn't say.", "storage_encrypted = true (with the customer's KMS key if they ask).")
            if after.get("publicly_accessible") is True:
                bad("public-db", "The database is reachable from the internet.", "publicly_accessible = false")
            if after.get("password") not in (None, "") and after.get("manage_master_user_password") is not True:
                bad("db-password-in-plan", "A literal DB password is in the plan, so it is in state and in your repo's history.", "manage_master_user_password = true, or a random_password stored in Secrets Manager.")
        if typ == "aws_ebs_volume" and after.get("encrypted") is not True:
            bad("unencrypted-storage", "EBS volume is not encrypted.", "encrypted = true")
        if typ == "aws_iam_access_key":
            bad("long-lived-key", "A long-lived access key. The brief says OIDC and role assumption.", "Delete it; use roles.")
        if typ == "aws_ecs_task_definition":
            for c in _containers(after):
                for e in c.get("environment") or []:
                    if SECRET_NAME.search(e.get("name", "")) and e.get("value"):
                        bad("secret-in-env", f"Container env {e['name']} holds a literal value.", "Use the `secrets` block with a Secrets Manager or SSM ARN.")
        if typ == "aws_cloudwatch_log_group" and not after.get("retention_in_days"):
            bad("log-retention", "Logs are kept forever (and billed forever). Their security team will also ask how long.", "Set retention_in_days to what the customer's policy says.")

    n = lambda *t: sum(counts.get(x, 0) for x in t)
    present = [
        {"id": "ecs", "label": "ECS Fargate service", "ok": n("aws_ecs_service") > 0},
        {"id": "alb", "label": "Internal load balancer", "ok": n("aws_lb", "aws_alb") > 0},
        {"id": "rds", "label": "RDS Postgres", "ok": n("aws_db_instance", "aws_rds_cluster") > 0},
        {"id": "secret", "label": "Secrets Manager secret", "ok": n("aws_secretsmanager_secret") > 0},
        {"id": "logs", "label": "CloudWatch log group", "ok": n("aws_cloudwatch_log_group") > 0},
        {"id": "dash", "label": "CloudWatch dashboard", "ok": n("aws_cloudwatch_dashboard") > 0},
        {"id": "alarms", "label": "At least two alarms", "ok": n("aws_cloudwatch_metric_alarm") >= 2},
        {"id": "oidc", "label": "GitHub OIDC provider (no AWS keys in CI)", "ok": n("aws_iam_openid_connect_provider") > 0},
    ]
    out.sort(key=lambda f: (f["address"], f["rule"]))
    return out, present, sum(counts.values())


def plan_report():
    p = lab_dir() / "infra" / "plan.json"
    if not p.exists():
        return {"ready": False, "how": "In lab/infra: terraform plan -out=plan.out && terraform show -json plan.out > plan.json"}
    try:
        plan = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ready": False, "how": "plan.json isn't valid JSON. Use `terraform show -json`, not `terraform show`."}
    findings, present, n = review_plan(plan)
    return {"ready": True, "resources": n, "findings": findings, "present": present, "plan_mtime": int(p.stat().st_mtime)}


# ---- the 30 minute drill ----

def _drills_path():
    return lab_dir() / "runs" / "drills.json"


def _load_drills():
    p = _drills_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"running": None, "drills": []}


def _save(d):
    _drills_path().parent.mkdir(parents=True, exist_ok=True)
    _drills_path().write_text(json.dumps(d, indent=2), encoding="utf-8")


def drill_state():
    d = _load_drills()
    d["bar_minutes"] = BAR_MINUTES
    return d


def drill_start(now=None):
    d = _load_drills()
    if d["running"]:
        return d
    d["running"] = {"started": now if now is not None else time.time()}
    _save(d)
    return d


def drill_stop(note="", now=None):
    d = _load_drills()
    if not d["running"]:
        raise ValueError("No drill is running. Start the timer when you run terraform destroy.")
    secs = (now if now is not None else time.time()) - d["running"]["started"]
    d["drills"].append({"finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "minutes": round(secs / 60, 1),
                        "within_bar": secs <= BAR_MINUTES * 60, "note": note.strip()[:300]})
    d["running"] = None
    _save(d)
    return d


def drill_cancel():
    d = _load_drills()
    d["running"] = None
    _save(d)


# ---- documents ----

DOCS = {
    "RUNBOOK.md": [("deploy", r"deploy"), ("roll back", r"roll(ing|ed)?\s*-?back|revert"), ("rotate the API key", r"rotat"),
                   ("read the dashboard", r"dashboard"), ("what each alarm means", r"alarm")],
    "HANDOVER.md": [("what the customer's team owns", r"own"), ("what they need to learn", r"learn|train|skill"), ("open risks", r"risk")],
}


def docs_report():
    out = []
    for name, wants in DOCS.items():
        p = lab_dir() / name
        if not p.exists():
            out.append({"doc": name, "exists": False, "sections": [{"label": w, "ok": False} for w, _ in wants]})
            continue
        text = p.read_text(encoding="utf-8")
        heads = [l.lstrip("# ").strip() for l in text.splitlines() if l.startswith("#")]
        out.append({"doc": name, "exists": True, "words": len(text.split()),
                    "sections": [{"label": w, "ok": any(re.search(rx, h, re.I) for h in heads)} for w, rx in wants]})
    return out


def state():
    return {"plan": plan_report(), "drill": drill_state(), "docs": docs_report(), "lab_path": "02-technical-depth/04-deploy-anywhere/lab"}
