# Go-live checklist: <customer>

## Before go-live
- [ ] Scenario suite passes at the agreed bar: ___ / ___ (run ID: ___)
- [ ] **Zero failures** on hard-rule scenarios (money limits, regulated topics, identity, fraud)
- [ ] Hard rules are enforced in tools, and I've seen each one refuse a talked-into-it request
- [ ] Escalation tested end to end: a real human on the customer's side received a test handoff
- [ ] Out-of-hours behaviour agreed and tested
- [ ] Customer sponsor has reviewed 10 sample transcripts and signed off in writing
- [ ] Rollout plan agreed: % of traffic / channels / hours for week 1
- [ ] Kill switch: who can turn the agent off, how, and how fast (tested)
- [ ] Dashboards live: automation rate, escalations, CSAT, errors
- [ ] Baseline metrics recorded for comparison

## Hypercare (first 2 weeks)
- [ ] Daily: sample 30 conversations, tag failures, fix the top cause, add a scenario for it
- [ ] Daily 15-min check-in with the customer's support lead (week 1)
- [ ] Weekly account report sent (metric vs target, top failures, fixes, asks)

## Exit hypercare when
- [ ] Metric at or above target for 5 consecutive days
- [ ] No hard-rule failures in production
- [ ] Customer's team knows how to report issues and read the dashboard
- [ ] Learnings added to the implementation playbook
