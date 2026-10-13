# Kata 15: map a ServiceNow incident to a Salesforce Case

**Time-box: 45 minutes.** Used in: 02/06 (the Salesforce half of the lab: account and case sync), any CRM-to-ticketing integration.

**The task.** Implement `incident_to_case` and `case_to_incident_patch` in `field_map.py`. `python -m pytest -q katas/15-field-mapping`.

**What this is really about.** Two systems never have the same model. Here ServiceNow has eight states and Salesforce has four, priority is computed on one side and a plain field on the other, and "Closed" means something different in each. The honest way to map them is to write the compromises down as data, make the lossy ones loud, and refuse to guess:
- a value you can't map is an error that names the field and the value, not a default of "Medium"
- an empty string is not the same as nothing: Salesforce rejects `""` for some fields
- limits are real (255 and 32,000 characters); cutting text is a decision, and the cut should be visible
- the key that makes a sync idempotent travels with the record (`ExternalId__c`)
- sending a change the other system will reject later, far from here, is worse than refusing it now
- a patch is only the fields that differ: it keeps your sync quiet and your audit log readable

**Then.** Where would these two tables live in your 02/06 app so that the customer's admin can change them without a deploy? Who owns them when the customer adds a state?
