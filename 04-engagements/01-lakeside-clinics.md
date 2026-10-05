# Engagement 1 — Lakeside Clinics

## Brief
Lakeside Clinics runs 14 outpatient clinics across Greater Accra and Ashanti. Patients book, reschedule and ask questions over WhatsApp: ~2,500 messages/day to 14 different clinic phones staffed by front-desk workers. Average response time is 4 hours. About 18% of booked patients don't show up.

## Stakeholder memos (they conflict on purpose)
- **CEO (sponsor):** "I want an AI that answers every patient instantly, 24/7, in English and Twi. Cut no-shows in half. Launch in 6 weeks for the anniversary."
- **Medical director:** "Under no circumstances may it give medical advice or anything resembling a diagnosis. Anything clinical goes to a nurse. I want to see every conversation it has in the first month."
- **Head of front desk:** "My staff are worried about their jobs. Also, half of our messages are voice notes."
- **IT contractor:** "Bookings live in a Postgres DB behind a PHP app I wrote in 2019. No API. I can give you a read replica and a stored procedure for creating bookings."

## Constraints
- Patient data is sensitive health data (Ghana Data Protection Act 2012). Data minimisation, a retention policy and access logging are required.
- Clinics have intermittent connectivity; the front-desk escalation inbox must work on low bandwidth.
- WhatsApp Business API (via a BSP), with its 24-hour session-window rules.

## Acceptance bar
- Eval set of ≥ 100 scripted conversations (English, Twi, mixed, voice-note transcripts) covering: booking, reschedule, cancel, opening hours, prices, **clinical questions** (must escalate, never advise), emergencies (must give emergency guidance and escalate immediately), abuse, prompt injection.
- **0** clinical-advice failures on the safety slice. ≥ 90% task success on the booking slice. Escalation has a target response time and a dashboard.
- Booking writes are idempotent (patient double-sends "yes" → one booking).
- Automated reminder flow with a measured (simulated) no-show impact model and stated assumptions.

## What a strong submission includes
- A scoping doc that **renegotiates** "every patient, 24/7, 6 weeks" into a phased plan the medical director signs.
- A plan for the front-desk staff (they become the escalation/review team). Adoption is part of the deployment.
- Field feedback: what would a product team need to make this repeatable for clinic network #2?

*This overlaps heavily with RunMySales. Reuse it and say so. FDEs reuse aggressively.*
