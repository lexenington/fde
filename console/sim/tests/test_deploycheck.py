import json

import pytest

from sim import config, deploycheck as dc


def rc(addr, typ, after, actions=("create",)):
    return {"address": addr, "type": typ, "change": {"actions": list(actions), "after": after}}


def rules(plan):
    return [(f["address"], f["rule"]) for f in dc.review_plan(plan)[0]]


@pytest.fixture
def lab():
    d = config.LABS_DIR / "04-deploy-anywhere" / "lab"
    (d / "infra").mkdir(parents=True)
    return d


def test_exposure_findings():
    plan = {"resource_changes": [
        rc("aws_lb.a", "aws_lb", {"internal": False}), rc("aws_lb.ok", "aws_lb", {"internal": True}),
        rc("aws_subnet.pub", "aws_subnet", {"map_public_ip_on_launch": True}),
        rc("aws_ecs_service.s", "aws_ecs_service", {"network_configuration": [{"assign_public_ip": True}]}),
        rc("aws_security_group.sg", "aws_security_group", {"ingress": [{"from_port": 22, "to_port": 22, "cidr_blocks": ["0.0.0.0/0"]}],
                                                           "egress": [{"from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}]}),
        rc("aws_vpc_security_group_ingress_rule.r", "aws_vpc_security_group_ingress_rule", {"cidr_ipv4": "0.0.0.0/0"}),
        rc("aws_db_instance.db", "aws_db_instance", {"publicly_accessible": True, "password": "hunter2"}),
        rc("aws_iam_access_key.k", "aws_iam_access_key", {}),
        rc("aws_cloudwatch_log_group.l", "aws_cloudwatch_log_group", {"retention_in_days": 0}),
    ]}
    got = set(rules(plan))
    assert {("aws_lb.a", "public-alb"), ("aws_subnet.pub", "public-subnet"), ("aws_ecs_service.s", "public-ip"),
            ("aws_security_group.sg", "open-ingress"), ("aws_security_group.sg", "open-egress"),
            ("aws_vpc_security_group_ingress_rule.r", "open-ingress"), ("aws_db_instance.db", "public-db"),
            ("aws_db_instance.db", "unencrypted-storage"), ("aws_db_instance.db", "db-password-in-plan"),
            ("aws_iam_access_key.k", "long-lived-key"), ("aws_cloudwatch_log_group.l", "log-retention")} == got


def test_https_egress_and_deletes_are_not_findings():
    plan = {"resource_changes": [
        rc("aws_security_group.sg", "aws_security_group", {"egress": [{"from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]}]}),
        rc("aws_lb.gone", "aws_lb", {"internal": False}, actions=("delete",))]}
    assert rules(plan) == []


def test_literal_secrets_in_container_env_are_found_but_secret_refs_are_fine():
    defs = json.dumps([{"name": "app", "environment": [{"name": "ANTHROPIC_API_KEY", "value": "sk-ant-x"}, {"name": "LOG_LEVEL", "value": "info"}],
                        "secrets": [{"name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:..."}]}])
    assert rules({"resource_changes": [rc("aws_ecs_task_definition.t", "aws_ecs_task_definition", {"container_definitions": defs})]}) == [("aws_ecs_task_definition.t", "secret-in-env")]


def test_required_components(lab):
    plan = {"resource_changes": [rc("aws_ecs_service.s", "aws_ecs_service", {}), rc("a1", "aws_cloudwatch_metric_alarm", {}), rc("a2", "aws_cloudwatch_metric_alarm", {})]}
    present = {p["id"]: p["ok"] for p in dc.review_plan(plan)[1]}
    assert present["ecs"] and present["alarms"] and not present["rds"] and not present["oidc"]
    (lab / "infra" / "plan.json").write_text(json.dumps(plan))
    assert dc.plan_report()["ready"] and dc.plan_report()["resources"] == 3


def test_plan_not_ready_messages(lab):
    assert "terraform show -json" in dc.plan_report()["how"]
    (lab / "infra" / "plan.json").write_text("Terraform will perform")
    assert "valid JSON" in dc.plan_report()["how"]


def test_drill_timer_checks_the_thirty_minute_bar(lab):
    dc.drill_start(now=1000)
    assert dc.drill_start(now=5000)["running"]["started"] == 1000          # a second start doesn't reset the clock
    d = dc.drill_stop("destroy+apply", now=1000 + 29 * 60)
    assert d["drills"][0]["within_bar"] and d["drills"][0]["minutes"] == 29.0 and d["running"] is None
    dc.drill_start(now=0)
    assert not dc.drill_stop(now=31 * 60)["drills"][1]["within_bar"]
    with pytest.raises(ValueError):
        dc.drill_stop()


def test_docs_need_the_sections_the_brief_asks_for(lab):
    (lab / "RUNBOOK.md").write_text("# Runbook\n## How to deploy\n## Rolling back\n## Rotate the API key\n## Alarms\n")
    r = {d["doc"]: d for d in dc.docs_report()}
    assert [s["ok"] for s in r["RUNBOOK.md"]["sections"]] == [True, True, True, False, True]
    assert not r["HANDOVER.md"]["exists"]
