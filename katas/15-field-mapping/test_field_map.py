import pytest

from field_map import MappingError, case_to_incident_patch, incident_to_case


def inc(**over):
    base = {"number": "INC0010007", "short_description": "VPN not connecting from home", "description": "Fails after the update.", "state": "2",
            "priority": "3", "sys_created_on": "2026-10-06 08:15:30", "caller_id": {"link": "x", "value": "abc"}}
    return {**base, **over}


def test_the_straightforward_mapping():
    c = incident_to_case(inc(caller_email="esi.tetteh@volta.example"))
    assert c == {"Subject": "VPN not connecting from home", "Description": "Fails after the update.", "Status": "Working", "Priority": "Medium",
                 "ExternalId__c": "INC0010007", "CreatedDate__c": "2026-10-06T08:15:30.000+0000", "ContactEmail__c": "esi.tetteh@volta.example"}


@pytest.mark.parametrize("state,status", [("1", "New"), ("2", "Working"), ("3", "Waiting on customer"), ("6", "Closed"), ("7", "Closed"), ("8", "Closed")])
def test_every_state(state, status):
    assert incident_to_case(inc(state=state))["Status"] == status


@pytest.mark.parametrize("prio,want", [("1", "High"), ("2", "High"), ("3", "Medium"), ("4", "Low"), ("5", "Low")])
def test_every_priority(prio, want):
    assert incident_to_case(inc(priority=prio))["Priority"] == want


def test_empty_description_is_none_not_an_empty_string():
    assert incident_to_case(inc(description="  "))["Description"] is None
    assert incident_to_case(inc(description=""))["Description"] is None


def test_text_is_trimmed():
    assert incident_to_case(inc(short_description="  Printer jam \n"))["Subject"] == "Printer jam"


def test_long_text_is_cut_with_one_ellipsis_character():
    s = incident_to_case(inc(short_description="x" * 400))["Subject"]
    assert len(s) == 255 and s.endswith("…") and s[:254] == "x" * 254
    d = incident_to_case(inc(description="y" * 40000))["Description"]
    assert len(d) == 32000 and d.endswith("…")
    assert incident_to_case(inc(short_description="z" * 255))["Subject"] == "z" * 255


def test_no_caller_email_is_none():
    assert incident_to_case(inc())["ContactEmail__c"] is None


@pytest.mark.parametrize("over", [{"state": "9"}, {"state": ""}, {"priority": "0"}, {"number": ""}, {"short_description": "   "}])
def test_what_cannot_be_mapped_is_refused_and_named(over):
    key = next(iter(over))
    with pytest.raises(MappingError, match=key.replace("_", ".?") if key != "number" else "number"):
        incident_to_case(inc(**over))


def test_a_missing_key_is_refused():
    d = inc()
    del d["number"]
    with pytest.raises(MappingError):
        incident_to_case(d)


def test_the_reverse_sends_only_what_changed():
    cur = inc(state="1")
    assert case_to_incident_patch({"Subject": "VPN not connecting from home", "Description": "Fails after the update.", "Status": "New"}, cur) == {}
    assert case_to_incident_patch({"Subject": "VPN down", "Status": "Working"}, cur) == {"short_description": "VPN down", "state": "2"}


def test_description_none_clears_it():
    assert case_to_incident_patch({"Description": None}, inc()) == {"description": ""}
    assert case_to_incident_patch({"Description": None}, inc(description="")) == {}


def test_priority_is_never_sent():
    assert case_to_incident_patch({"Priority": "High"}, inc(priority="5")) == {}


def test_waiting_on_customer():
    assert case_to_incident_patch({"Status": "Waiting on customer"}, inc()) == {"state": "3"}


def test_closing_needs_a_resolution():
    with pytest.raises(MappingError, match="(?i)resolution"):
        case_to_incident_patch({"Status": "Closed"}, inc())
    assert case_to_incident_patch({"Status": "Closed", "Resolution__c": "Replaced the router."}, inc()) == {
        "state": "7", "close_code": "Solved (Permanently)", "close_notes": "Replaced the router."}


def test_a_closed_incident_cannot_be_changed():
    for state in ("7", "8"):
        with pytest.raises(MappingError, match="(?i)closed|read-only"):
            case_to_incident_patch({"Subject": "New title"}, inc(state=state))
    assert case_to_incident_patch({"Subject": "VPN not connecting from home"}, inc(state="7")) == {}


def test_an_unknown_status_is_refused():
    with pytest.raises(MappingError, match="Status"):
        case_to_incident_patch({"Status": "Escalated"}, inc())
