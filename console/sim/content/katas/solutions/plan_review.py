def review(plan):
    out = set()
    for rc in plan.get("resource_changes") or []:
        ch = rc.get("change") or {}
        after = ch.get("after")
        if after is None or not ({"create", "update"} & set(ch.get("actions") or [])):
            continue
        addr, typ = rc["address"], rc["type"]
        if typ == "aws_instance" and after.get("associate_public_ip_address") is True:
            out.add((addr, "public-ip"))
        if typ == "aws_security_group":
            for r in after.get("ingress") or []:
                world = "0.0.0.0/0" in (r.get("cidr_blocks") or []) or "::/0" in (r.get("ipv6_cidr_blocks") or [])
                if world and not (r.get("from_port") == 443 and r.get("to_port") == 443):
                    out.add((addr, "open-ingress"))
        if typ == "aws_db_instance":
            if after.get("storage_encrypted") is not True:
                out.add((addr, "unencrypted-storage"))
            if after.get("publicly_accessible") is True:
                out.add((addr, "public-db"))
        if typ == "aws_ebs_volume" and after.get("encrypted") is not True:
            out.add((addr, "unencrypted-storage"))
        if typ == "aws_iam_access_key":
            out.add((addr, "long-lived-key"))
    return [{"address": a, "rule": r, "severity": "high"} for a, r in sorted(out)]
