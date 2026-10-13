from datetime import datetime


class MappingError(ValueError):
    pass


STATUS = {"1": "New", "2": "Working", "3": "Waiting on customer", "6": "Closed", "7": "Closed", "8": "Closed"}
PRIORITY = {"1": "High", "2": "High", "3": "Medium", "4": "Low", "5": "Low"}
BACK = {"New": "1", "Working": "2", "Waiting on customer": "3"}


def _cut(text, limit):
    return text if len(text) <= limit else text[:limit - 1] + "…"


def incident_to_case(inc):
    number = (inc.get("number") or "").strip()
    if not number:
        raise MappingError("number is missing: the incident number is the sync key")
    subject = (inc.get("short_description") or "").strip()
    if not subject:
        raise MappingError("short_description is empty")
    state, prio = inc.get("state"), inc.get("priority")
    if state not in STATUS:
        raise MappingError(f"state {state!r} has no Salesforce Status")
    if prio not in PRIORITY:
        raise MappingError(f"priority {prio!r} has no Salesforce Priority")
    desc = (inc.get("description") or "").strip()
    created = datetime.strptime(inc["sys_created_on"], "%Y-%m-%d %H:%M:%S")
    return {"Subject": _cut(subject, 255), "Description": _cut(desc, 32000) if desc else None, "Status": STATUS[state], "Priority": PRIORITY[prio],
            "ExternalId__c": number, "CreatedDate__c": created.strftime("%Y-%m-%dT%H:%M:%S.000+0000"), "ContactEmail__c": inc.get("caller_email") or None}


def case_to_incident_patch(case, current):
    patch = {}
    if "Subject" in case and case["Subject"] != current.get("short_description"):
        patch["short_description"] = case["Subject"]
    if "Description" in case:
        new = case["Description"] or ""
        if new != (current.get("description") or ""):
            patch["description"] = new
    if "Status" in case:
        s = case["Status"]
        if s == "Closed":
            if not case.get("Resolution__c"):
                raise MappingError("Status Closed needs a Resolution__c: ServiceNow requires a resolution code and notes to close")
            if current.get("state") != "7":
                patch.update({"state": "7", "close_code": "Solved (Permanently)", "close_notes": case["Resolution__c"]})
        elif s in BACK:
            if BACK[s] != current.get("state"):
                patch["state"] = BACK[s]
        else:
            raise MappingError(f"Status {s!r} has no ServiceNow state")
    if patch and current.get("state") in ("7", "8"):
        raise MappingError("the incident is closed (read-only in ServiceNow); open a new one")
    return patch
