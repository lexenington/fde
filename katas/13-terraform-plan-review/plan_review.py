"""Kata 13: review a Terraform plan like the customer's platform team will.

`terraform plan -out=plan.out && terraform show -json plan.out > plan.json` gives the JSON. You'll be asked to
justify every public thing you deploy. Catch the obvious ones before they do.
"""


def review(plan: dict) -> list[dict]:
    """Return findings for the resources the plan would create or update.

    `plan["resource_changes"]` is a list of `{"address": "aws_instance.web", "type": "aws_instance",
    "change": {"actions": ["create"], "after": {...planned attributes...}}}`. Only look at changes whose actions
    include "create" or "update". Ignore "delete", "no-op" and "read", and changes whose `after` is null.

    Findings, as `{"address": ..., "rule": ..., "severity": "high"}`:
      "public-ip"            aws_instance with associate_public_ip_address true
      "open-ingress"         aws_security_group with an ingress rule open to the world (cidr_blocks containing
                             "0.0.0.0/0", or ipv6_cidr_blocks containing "::/0") on anything other than exactly
                             port 443 (from_port 443 and to_port 443)
      "unencrypted-storage"  aws_db_instance whose storage_encrypted is not true, or aws_ebs_volume whose
                             encrypted is not true
      "public-db"            aws_db_instance with publicly_accessible true
      "long-lived-key"       any aws_iam_access_key
    A resource can have several findings. Return them sorted by (address, rule); no findings gives [].
    """
    raise NotImplementedError
