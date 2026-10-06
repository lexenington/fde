from plan_review import review


def rc(address, type_, after, actions=("create",)):
    return {"address": address, "type": type_, "change": {"actions": list(actions), "after": after}}


def plan(*changes):
    return {"format_version": "1.2", "resource_changes": list(changes)}


def rules(findings):
    return [(f["address"], f["rule"]) for f in findings]


def test_an_empty_plan_has_no_findings():
    assert review({}) == [] and review(plan()) == []


def test_a_public_ip_on_an_instance():
    p = plan(rc("aws_instance.web", "aws_instance", {"associate_public_ip_address": True}),
             rc("aws_instance.app", "aws_instance", {"associate_public_ip_address": False}),
             rc("aws_instance.other", "aws_instance", {}))
    assert rules(review(p)) == [("aws_instance.web", "public-ip")]


def test_findings_are_high_severity_and_have_the_documented_shape():
    f = review(plan(rc("aws_iam_access_key.ci", "aws_iam_access_key", {"user": "ci"})))
    assert f == [{"address": "aws_iam_access_key.ci", "rule": "long-lived-key", "severity": "high"}]


def test_ingress_open_to_the_world_except_https():
    sg = lambda ingress: plan(rc("aws_security_group.sg", "aws_security_group", {"ingress": ingress}))
    assert rules(review(sg([{"from_port": 22, "to_port": 22, "cidr_blocks": ["0.0.0.0/0"]}]))) == [("aws_security_group.sg", "open-ingress")]
    assert rules(review(sg([{"from_port": 0, "to_port": 65535, "cidr_blocks": ["10.0.0.0/8", "0.0.0.0/0"]}]))) == [("aws_security_group.sg", "open-ingress")]
    assert rules(review(sg([{"from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]}]))) == []
    assert rules(review(sg([{"from_port": 443, "to_port": 8443, "cidr_blocks": ["0.0.0.0/0"]}]))) == [("aws_security_group.sg", "open-ingress")]
    assert rules(review(sg([{"from_port": 22, "to_port": 22, "cidr_blocks": ["10.0.0.0/16"]}]))) == []
    assert rules(review(sg([{"from_port": 80, "to_port": 80, "cidr_blocks": [], "ipv6_cidr_blocks": ["::/0"]}]))) == [("aws_security_group.sg", "open-ingress")]


def test_one_finding_per_rule_even_with_several_open_rules():
    ingress = [{"from_port": 22, "to_port": 22, "cidr_blocks": ["0.0.0.0/0"]}, {"from_port": 80, "to_port": 80, "cidr_blocks": ["0.0.0.0/0"]}]
    assert rules(review(plan(rc("aws_security_group.sg", "aws_security_group", {"ingress": ingress})))) == [("aws_security_group.sg", "open-ingress")]


def test_unencrypted_storage_and_public_databases():
    p = plan(rc("aws_db_instance.db", "aws_db_instance", {"storage_encrypted": False, "publicly_accessible": True}),
             rc("aws_db_instance.ok", "aws_db_instance", {"storage_encrypted": True, "publicly_accessible": False}),
             rc("aws_ebs_volume.v", "aws_ebs_volume", {"encrypted": False}),
             rc("aws_ebs_volume.missing", "aws_ebs_volume", {}),
             rc("aws_ebs_volume.fine", "aws_ebs_volume", {"encrypted": True}))
    assert rules(review(p)) == [("aws_db_instance.db", "public-db"), ("aws_db_instance.db", "unencrypted-storage"),
                                ("aws_ebs_volume.missing", "unencrypted-storage"), ("aws_ebs_volume.v", "unencrypted-storage")]


def test_a_missing_encryption_setting_counts_as_unencrypted():
    assert rules(review(plan(rc("aws_db_instance.x", "aws_db_instance", {})))) == [("aws_db_instance.x", "unencrypted-storage")]


def test_only_creates_and_updates_are_reviewed():
    bad = {"associate_public_ip_address": True}
    p = plan(rc("aws_instance.a", "aws_instance", bad, actions=("update",)),
             rc("aws_instance.b", "aws_instance", bad, actions=("delete", "create")),
             rc("aws_instance.c", "aws_instance", bad, actions=("delete",)),
             rc("aws_instance.d", "aws_instance", bad, actions=("no-op",)),
             rc("aws_instance.e", "aws_instance", bad, actions=("read",)),
             rc("aws_instance.f", "aws_instance", None, actions=("delete",)))
    assert rules(review(p)) == [("aws_instance.a", "public-ip"), ("aws_instance.b", "public-ip")]


def test_results_are_sorted_by_address_then_rule():
    p = plan(rc("aws_instance.z", "aws_instance", {"associate_public_ip_address": True}),
             rc("aws_db_instance.a", "aws_db_instance", {"publicly_accessible": True}),
             rc("aws_iam_access_key.k", "aws_iam_access_key", {}))
    assert rules(review(p)) == [("aws_db_instance.a", "public-db"), ("aws_db_instance.a", "unencrypted-storage"),
                                ("aws_iam_access_key.k", "long-lived-key"), ("aws_instance.z", "public-ip")]
