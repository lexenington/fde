# Engagement 1 — Lakeside Clinics

## Brief
Lakeside Clinics runs 14 outpatient clinics across Greater Accra and Ashanti. Patients book, reschedule and ask questions over WhatsApp: ~2,500 messages/day to 14 different clinic phones staffed by front-desk workers. Average response time is 4 hours. About 18% of booked patients don't show up.

## Stakeholder memos (they conflict on purpose)
- **CEO (sponsor):** "I want an AI that answers every patient instantly, 24/7, in English and Twi. Cut no-shows in half. Launch in 6 weeks for the anniversary."
- **Medical director:** "Under no circumstances may it give medical advice or anything resembling a diagnosis. Anything clinical goes to a nurse. I want to see every conversation it has in the first month."
- **Head of front desk:** "My staff are worried about their jobs. Also, half of our messages are voice notes."
- **IT contractor:** "Bookings live in a Postgres DB behind a PHP app I wrote in 2019. No API. I can give you a read replica and a stored procedure for creating bookings."

## The world
The customer's systems are simulated for you: [04-engagements/lakeside/WORLD.md](lakeside/WORLD.md). `docker compose up --build` in `console/`, then *Engagements → 1 Lakeside Clinics* at http://localhost:3300 gives you the legacy database, the WhatsApp provider, speech-to-text, a patient phone to test with, and the customer's acceptance test.

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

## Stretch: the phone line
Plenty of Lakeside's patients don't use WhatsApp at all. They call the clinic, and nobody answers at 7 pm. Postings increasingly ask for voice agent and telephony experience, and a real phone line exposes problems a chat bot never meets. **The Console doesn't simulate this one.** You use a real voice provider with a test number, and only after the WhatsApp acceptance bar is met.

Build a phone agent that books, reschedules and cancels through the same booking path as your WhatsApp bot, then deal with the parts that make voice hard:

- **Provider and number.** Find out which providers can actually give you an inbound number that callers in Ghana can reach, and at what per-minute cost (Africa's Talking, Twilio, or a SIP trunk from a local telco). Registration and number provisioning can take days, so start early, and write down what the provider needed from you. The customer will have to do the same.
- **Latency budget.** Write down a target for the time from the caller stopping speaking to the agent starting to speak, then measure p50/p95 on real calls. Break it down by stage (speech-to-text, model, text-to-speech, network) and decide where to cut.
- **Turn-taking.** The caller talks over the agent ("barge-in"), goes silent, or is on a noisy tro-tro. Decide what happens in each case and test it.
- **Language.** English, Twi and code-switched callers. Compare at least two speech-to-text options on your own recorded Twi clips (for example a general-purpose model vs. a Ghana-focused one such as GhanaNLP's) and report word error rate on the booking-critical words: names, clinic names, dates, times.
- **Confirmation.** Spoken dates and phone numbers are easy to mishear. Decide what the agent reads back before it writes a booking, and confirm by SMS or WhatsApp.
- **Handover.** "I want to speak to a person" and anything clinical gets a warm transfer to the clinic's line, or a callback promise with a time, inside opening hours. Outside them, emergency guidance, then the escalation inbox.
- **Abuse.** Prank calls, silence, abusive callers, the same number calling 40 times, a recorded voice trying a prompt injection. Rate limits and a clear, polite way to end a call.
- **Cost.** Cost per completed booking call (telephony minutes + STT + model + TTS), next to the WhatsApp cost per booking.

**Deliver:** a phone slice in your eval (≥ 20 scripted calls, including recorded Twi), the latency table, and a half-page `VOICE.md` for Kwame: what it costs per call, what it can't do yet, and what the clinic must provide (a number, a transfer line, someone answering transfers).

*This overlaps heavily with RunMySales. Reuse it and say so. FDEs reuse aggressively.*
