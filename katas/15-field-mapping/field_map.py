"""Kata 15: map a ServiceNow incident to a Salesforce Case and back, without lying about what is lost.

Every integration is two data models and a table of compromises. Write the table in code, with tests.
"""


class MappingError(ValueError):
    """The record can't be mapped without guessing. Say why; never guess."""


def incident_to_case(inc: dict) -> dict:
    """ServiceNow incident (as the Table API returns it: every value a string, reference fields as {"link","value"}
    objects) -> the Salesforce Case body to POST/PATCH.

      Subject            short_description, trimmed; at most 255 characters (cut and end with "…", the single character)
      Description        description, trimmed; None when empty (Salesforce rejects ""); at most 32000 characters, same rule
      Status             from `state`:  "1" New, "2" Working, "3" Waiting on customer, "6" Closed, "7" Closed, "8" Closed
      Priority           from `priority`: "1" High, "2" High, "3" Medium, "4" Low, "5" Low
      ExternalId__c      number (the incident number is the key that makes the sync idempotent)
      CreatedDate__c     sys_created_on ("2026-10-06 08:15:30", UTC) -> "2026-10-06T08:15:30.000+0000"
      ContactEmail__c    the caller's email when the incident carries one in `caller_email`, else None

    Raise MappingError (naming the field and the value) for a `state` or `priority` not in the tables, for a missing
    `number`, and for a `short_description` that is empty after trimming. Don't invent defaults for them.
    """
    raise NotImplementedError


def case_to_incident_patch(case: dict, current: dict) -> dict:
    """A changed Salesforce Case -> the PATCH to send to the ServiceNow incident `current`: only the fields that differ.

      Subject      -> short_description          Description -> description (None -> "")
      Status       -> state:  New "1", Working "2", Waiting on customer "3"; "Closed" is only mappable when you also
                      have a `Resolution__c`: then state "7", close_code "Solved (Permanently)", close_notes = the resolution.
                      Closed without a resolution raises MappingError (ServiceNow's own business rule would reject it with a 403
                      later and far from here).
      Priority     -> NOT sent: priority in ServiceNow is computed from urgency and impact. Silently dropped.

    A closed incident (`current["state"]` in "7", "8") is read-only in ServiceNow: raise MappingError if anything would change.
    Return {} when nothing differs. Values are strings, as ServiceNow wants.
    """
    raise NotImplementedError
