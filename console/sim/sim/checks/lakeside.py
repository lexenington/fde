"""Lakeside Clinics: customer acceptance test (UAT).

Sends scripted patient conversations to the learner's WhatsApp bot through the simulated provider, waits for its
replies, then checks the replies, the legacy database and the bot's escalation list against hidden expectations
(content/uat/lakeside.json). It is the engagement's "customer says yes or no" moment.

Contract: 04-engagements/lakeside/WORLD.md
"""

import json
import re
import time
import urllib.parse
from datetime import date, datetime, timedelta

import httpx

from .. import bsp, config, lakeside_db as db
from ..crm import store
from .base import Blocked, Check, Fail, Suite

REPLY_TIMEOUT = 75.0      # a slow LLM bot is fine; no reply to the FIRST message in this long is a failure
FOLLOW_UP_TIMEOUT = 15.0  # later messages ("yes", "thanks") may legitimately get no reply
SETTLE = 3.0              # quiet time after the last reply before the next patient message
WORKERS = 3
TEST_NATIONALS = ("24999", "25999")     # prefixes of every number this suite creates

CLINICAL_ADVICE = [
    r"\b\d+(\.\d+)?\s*(mg|mcg|ml|g|tablets?|pills?|tabs?|capsules?|drops|teaspoons?|tsp)\b",
    r"\b(take|give|use|try)\s+(him|her|them|the child|your child|it|some)?\s*(some\s+)?(paracetamol|ibuprofen|aspirin|amoxicillin|antibiotics?|acetaminophen|panadol|brufen|coartem|artemether)",
    r"\byou\s+(probably|likely|may|might|could|seem to|appear to)\s+have\b",
    r"\bit('s| is| sounds like| could be| might be| may be)\s+(probably\s+|likely\s+)?(malaria|typhoid|an infection|pneumonia|anaemia|anemia|hypertension|diabetes|a virus)",
    r"\b(yes[, ]+you can|it is safe to|it's safe to|safe to take)\b",
    r"\bdosage\b",
]
CONFIRM_CLAIM = (r"(is|are|has been|have been|was|now|been)\s+(successfully\s+)?(confirmed|booked)|you('re| are)\s+(all set|booked)|"
                 r"booking\s+(is\s+)?confirmed|appointment\s+(is\s+)?confirmed|successfully booked")


def spec() -> dict:
    return json.loads((config.CONTENT_DIR / "uat" / "lakeside.json").read_text(encoding="utf-8"))


def business_days(n: int = 8) -> list[date]:
    out, d = [], date.today()
    while len(out) < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            out.append(d)
    return out


def natural(d: date) -> str:
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B')}"


class Ctx:
    def __init__(self):
        self.run_id = time.strftime("%Y%m%d-%H%M%S")
        self.learner_url = store.learner_url.rstrip("/")
        self.status: dict[str, str] = {}
        self.days = business_days()
        self.http = httpx.Client(base_url=self.learner_url, timeout=15)

    def fill(self, text: str) -> str:
        for i, d in enumerate(self.days, 1):
            text = text.replace("{d%d}" % i, natural(d))
        return text


# ---------------- database helpers (admin connection) ----------------

def national(prefix_idx: int, idx: int) -> str:
    return f"{TEST_NATIONALS[prefix_idx]}{idx:04d}"


def clinic_id(cur, name: str) -> int:
    row = cur.execute("SELECT clinic_id FROM tbl_clinic WHERE clinic_nm ILIKE %s ORDER BY clinic_id LIMIT 1", (f"%{name}%",)).fetchone()
    if not row:
        raise Fail(f"(test bug) unknown clinic {name!r}")
    return row[0]


def ensure_slot(cur, ctx: Ctx, clinic: str, day: int, hhmm: str, svc: str = "GEN") -> int:
    """Return an open, empty slot at that clinic/day/time, creating or clearing it if needed."""
    cid = clinic_id(cur, clinic)
    dt = datetime.combine(ctx.days[day - 1], datetime.strptime(hhmm, "%H:%M").time())
    row = cur.execute("SELECT slot_id FROM tbl_slot WHERE clinic_id = %s AND slot_dt = %s", (cid, dt)).fetchone()
    if row:
        sid = row[0]
        cur.execute("DELETE FROM tbl_appt WHERE slot_id = %s", (sid,))
        cur.execute("UPDATE tbl_slot SET slot_st = 'O', svc_code = %s WHERE slot_id = %s", (svc, sid))
    else:
        sid = cur.execute("INSERT INTO tbl_slot (clinic_id, slot_dt, svc_code, slot_st) VALUES (%s,%s,%s,'O') RETURNING slot_id",
                          (cid, dt, svc)).fetchone()[0]
    return sid


def insert_patient(cur, phone: str, first: str, last: str) -> int:
    return cur.execute("INSERT INTO tbl_pt (pt_fname, pt_lname, pt_phone, pt_created) VALUES (%s,%s,%s,now()) RETURNING pt_id",
                       (first, last, phone)).fetchone()[0]


def cleanup_test_data(cur):
    like = " OR ".join(f"right(regexp_replace(coalesce(pt_phone,''),'\\D','','g'),9) LIKE '{p}%%'" for p in TEST_NATIONALS)
    cur.execute(f"""UPDATE tbl_slot SET slot_st = 'O' WHERE slot_id IN
                    (SELECT slot_id FROM tbl_appt WHERE pt_id IN (SELECT pt_id FROM tbl_pt WHERE {like}))""")
    cur.execute(f"DELETE FROM tbl_appt WHERE pt_id IN (SELECT pt_id FROM tbl_pt WHERE {like})")
    cur.execute(f"DELETE FROM tbl_pt WHERE {like}")


# ---------------- one conversation ----------------

class Conversation:
    def __init__(self, ctx: Ctx, idx: int, spec: dict):
        self.ctx, self.idx, self.spec = ctx, idx, spec
        self.nat = national(0, idx)
        self.phone = f"+233{self.nat}"
        self.refs: list[int] = []
        self.sent: list[tuple[float, str]] = []     # (time, what the patient sent)
        self.cancel_baseline = 0
        self.started = time.time()

    # --- setup ---
    def setup(self):
        with db.connect() as conn:
            cur = conn.cursor()
            prepared = set()
            for step in self.spec["setup"]:
                a = next(iter(step.values()))
                if isinstance(a, dict) and "clinic" in a:
                    prepared.add((a["clinic"], a["day"], a["time"]))
            for pred in self.spec["expect"]:     # a booking can only succeed if its slot is open
                arg = pred.get("booking")
                if arg and (arg["clinic"], arg["day"], arg["time"]) not in prepared:
                    ensure_slot(cur, self.ctx, arg["clinic"], arg["day"], arg["time"], arg.get("svc", "GEN"))
            for step in self.spec["setup"]:
                kind, a = next(iter(step.items()))
                if kind == "backup_window":
                    db.set_backup_window(True)
                elif kind == "slot":
                    ensure_slot(cur, self.ctx, a["clinic"], a["day"], a["time"], a.get("svc", "GEN"))
                elif kind == "patient":
                    phone = f"0{self.nat}" if a.get("format") == "local" else self.phone
                    insert_patient(cur, phone, a.get("first", ""), a.get("last", ""))
                elif kind in ("book", "block"):
                    who = "other" if kind == "block" else a.get("who", "self")
                    sid = ensure_slot(cur, self.ctx, a["clinic"], a["day"], a["time"], a.get("svc", "GEN"))
                    if who == "self":
                        row = cur.execute("SELECT pt_id FROM tbl_pt WHERE right(regexp_replace(coalesce(pt_phone,''),'\\D','','g'),9) = %s", (self.nat,)).fetchone()
                        pt = row[0] if row else insert_patient(cur, self.phone, "", "")
                    else:
                        pt = insert_patient(cur, f"+233{national(1, self.idx)}", a.get("first", "Other"), a.get("last", "Patient"))
                    appt = cur.execute("INSERT INTO tbl_appt (pt_id, slot_id, booked_on, appt_st) VALUES (%s,%s,now(),'B') RETURNING appt_id", (pt, sid)).fetchone()[0]
                    cur.execute("UPDATE tbl_slot SET slot_st = 'B' WHERE slot_id = %s", (sid,))
                    self.refs.append(appt)
            self.cancel_baseline = self.cancelled_count(cur)

    def cancelled_count(self, cur) -> int:
        cond = " AND ".join(f"right(regexp_replace(coalesce(p.pt_phone,''),'\\D','','g'),9) NOT LIKE '{p}%%'" for p in TEST_NATIONALS)
        return cur.execute(f"SELECT count(*) FROM tbl_appt a JOIN tbl_pt p ON p.pt_id = a.pt_id WHERE a.appt_st = 'C' AND {cond}").fetchone()[0]

    # --- the patient talks ---
    def talk(self):
        for turn in self.spec["turns"]:
            if isinstance(turn, str):
                turn = {"text": turn}
            t0 = time.time()
            if "voice" in turn:
                v = turn["voice"]
                mid = bsp.register_voice(self.ctx.fill(v["transcript"]), v.get("language", "en"), v.get("confidence", 0.9))
                sent = "(voice note) " + self.ctx.fill(v["transcript"])
                res = bsp.inbound(self.phone, voice=mid)
            else:
                sent = self.ctx.fill(turn["text"])
                res = bsp.inbound(self.phone, text=sent, times=turn.get("times", 1), message_id=None)
            self.sent.append((t0, sent))
            bad = [c for c in res["webhook_status"] if c is None or not 200 <= c < 300]
            if bad:
                raise Fail(f"your webhook /webhooks/whatsapp answered {res['webhook_status']} to a patient message. "
                           "It must acknowledge every inbound message with 2xx (even duplicates), quickly, then do the work.")
            self.wait_for_reply(t0)
        time.sleep(2.0)       # late replies and escalations

    def wait_for_reply(self, since: float):
        patience = FOLLOW_UP_TIMEOUT if self.replies() else REPLY_TIMEOUT
        while True:
            now = time.time()
            msgs = bsp.outbound_since(self.phone, since)
            if msgs and now - max(m["at"] for m in msgs) > SETTLE:
                return
            if not msgs and now - since > patience:
                return
            if now - since > REPLY_TIMEOUT * 2:
                return
            time.sleep(0.4)

    # --- evidence ---
    def replies(self) -> list[dict]:
        return bsp.outbound_since(self.phone, self.started)

    def reply_text(self) -> str:
        return "\n".join(m["body"] for m in self.replies())

    def transcript(self) -> str:
        events = [(t, "PATIENT", s) for t, s in self.sent] + [(m["at"], "BOT", m["body"]) for m in self.replies()]
        return "\n".join(f"{who}: {txt}" for _, who, txt in sorted(events, key=lambda e: e[0]))

    def appts(self) -> list[tuple]:
        with db.connect() as conn:
            return conn.execute("""SELECT a.appt_id, a.appt_st, s.slot_dt, c.clinic_nm, s.svc_code, s.slot_id
                                   FROM tbl_appt a JOIN tbl_pt p ON p.pt_id = a.pt_id JOIN tbl_slot s ON s.slot_id = a.slot_id
                                   JOIN tbl_clinic c ON c.clinic_id = s.clinic_id
                                   WHERE right(regexp_replace(coalesce(p.pt_phone,''),'\\D','','g'),9) = %s""", (self.nat,)).fetchall()

    def escalations(self) -> list[dict] | None:
        try:
            r = self.ctx.http.get("/api/escalations", params={"phone": self.phone})
        except httpx.HTTPError:
            return None
        if r.status_code != 200:
            return None
        data = r.json()
        return data.get("escalations", []) if isinstance(data, dict) else data

    # --- predicates ---
    def check(self, pred: dict) -> str | None:
        """None if the expectation holds, otherwise a plain-words reason."""
        (name, arg), = pred.items()
        text = self.reply_text().lower()
        active = [a for a in self.appts() if a[1] == "B"]
        if name == "booking":
            dt = datetime.combine(self.ctx.days[arg["day"] - 1], datetime.strptime(arg["time"], "%H:%M").time())
            hits = [a for a in active if a[2] == dt and arg["clinic"].lower() in a[3].lower() and (not arg.get("svc") or a[4] == arg["svc"])]
            want = arg.get("count", 1)
            if len(hits) != want:
                where = ", ".join(f"{a[3]} {a[2]:%a %d %b %H:%M}" for a in active) or "no active bookings"
                return f"expected {want} booking(s) at {arg['clinic']} on {dt:%a %d %b} {arg['time']}; the database has: {where}"
        elif name == "no_booking":
            if active:
                return "a booking was created but should not have been: " + ", ".join(f"{a[3]} {a[2]:%a %d %b %H:%M}" for a in active)
        elif name == "max_active_bookings":
            if len(active) > arg:
                return f"{len(active)} active bookings for this patient; at most {arg} allowed"
        elif name == "one_patient_record":
            with db.connect() as conn:
                n = conn.execute("SELECT count(*) FROM tbl_pt WHERE right(regexp_replace(coalesce(pt_phone,''),'\\D','','g'),9) = %s", (self.nat,)).fetchone()[0]
            if n != 1:
                return f"{n} patient records for this number (a returning patient was duplicated, probably by a different phone format)"
        elif name == "slot_not_double_booked":
            dt = datetime.combine(self.ctx.days[arg["day"] - 1], datetime.strptime(arg["time"], "%H:%M").time())
            with db.connect() as conn:
                n = conn.execute("""SELECT count(*) FROM tbl_appt a JOIN tbl_slot s ON s.slot_id = a.slot_id JOIN tbl_clinic c ON c.clinic_id = s.clinic_id
                                    WHERE a.appt_st = 'B' AND s.slot_dt = %s AND c.clinic_nm ILIKE %s""", (dt, f"%{arg['clinic']}%")).fetchone()[0]
            if n > 1:
                return f"the slot now has {n} active appointments (double-booked)"
        elif name == "appt_status":
            with db.connect() as conn:
                row = conn.execute("SELECT appt_st FROM tbl_appt WHERE appt_id = %s", (self.refs[arg["ref"]],)).fetchone()
            got = row[0] if row else "(deleted)"
            if got != arg["status"]:
                return f"the pre-existing appointment has status {got!r}, expected {arg['status']!r}"
        elif name == "no_cancellations":
            with db.connect() as conn:
                now = self.cancelled_count(conn.cursor())
            if now != self.cancel_baseline:
                return f"{now - self.cancel_baseline} appointment(s) belonging to other patients were cancelled"
        elif name in ("escalated", "not_escalated"):
            esc = self.escalations()
            if esc is None:
                return "GET /api/escalations?phone=... did not return a JSON list (see WORLD.md)"
            kind = arg.get("kind", "*")
            found = [e for e in esc if kind == "*" or str(e.get("kind", "")).lower() == kind]
            if name == "escalated" and not found:
                return f"no {'' if kind == '*' else kind + ' '}escalation was recorded for this patient (your list had {len(esc)} item(s))"
            if name == "not_escalated" and found:
                return "an escalation was recorded but should not have been"
        elif name == "reply_has_any":
            if not any(w.lower() in text for w in arg):
                return f"none of {arg} appears in the replies"
        elif name == "reply_has_all":
            miss = [w for w in arg if w.lower() not in text]
            if miss:
                return f"the replies do not mention {miss}"
        elif name == "first_reply_has_any":
            r = self.replies()
            if not r:
                return "no reply at all"
            if not any(w.lower() in r[0]["body"].lower() for w in arg):
                return f"the FIRST reply must contain one of {arg}; it said: {r[0]['body'][:140]!r}"
        elif name == "reply_lacks":
            for pat in arg:
                m = re.search(pat, text, re.I)
                if m:
                    return f"a reply contains {m.group(0)!r}, which it must not"
        elif name == "no_clinical_advice":
            for pat in CLINICAL_ADVICE + [re.escape(w) for w in arg.get("extra", [])]:
                m = re.search(pat, text, re.I)
                if m:
                    return f"a reply gives clinical advice or a diagnosis ({m.group(0)!r}). The answer to a clinical question is a nurse, never an answer"
        elif name == "no_confirmation_claim":
            m = re.search(CONFIRM_CLAIM, text, re.I)
            if m:
                return f"a reply claims the booking is done ({m.group(0)!r}) but nothing was written to the database"
        elif name == "price":
            with db.connect() as conn:
                price = conn.execute("SELECT price_ghs FROM tbl_svc WHERE svc_code = %s", (arg,)).fetchone()[0]
            whole = int(price)
            if not re.search(rf"(?<![\d.]){whole}(\.00)?(?![\d])", text):
                return f"the price GHS {whole} does not appear in the replies"
        elif name == "no_foreign_pii":
            with db.connect() as conn:
                known = {r[0] for r in conn.execute("SELECT right(regexp_replace(coalesce(pt_phone,''),'\\D','','g'),9) FROM tbl_pt")}
            for m in re.finditer(r"\+?\d[\d\s\-]{7,}\d", self.reply_text()):
                n9 = re.sub(r"\D", "", m.group(0))[-9:]
                if n9 in known and n9 != self.nat:
                    return f"a reply contains another patient's phone number ({m.group(0).strip()})"
        elif name == "max_outbound":
            if len(self.replies()) > arg:
                return f"{len(self.replies())} messages sent for this conversation; expected at most {arg} (are you replying to duplicates?)"
        elif name == "any_of":
            reasons = [self.check(p) for p in arg]
            if all(reasons):
                return "none of the acceptable outcomes happened: " + " | ".join(reasons)
        else:
            return f"(test bug) unknown expectation {name!r}"
        return None


def run_conversation(ctx: Ctx, idx: int, sp: dict) -> str:
    conv = Conversation(ctx, idx, sp)
    try:
        conv.setup()
        conv.talk()
        if not conv.replies():
            raise Fail(f"your bot never replied (waited {REPLY_TIMEOUT:.0f}s after each message).\n--- conversation ---\n{conv.transcript()}")
        problems = [r for r in (conv.check(p) for p in sp["expect"]) if r]
        if problems:
            raise Fail("; ".join(problems) + "\n--- conversation ---\n" + conv.transcript())
        first = conv.replies()[0]["at"] - conv.sent[0][0]
        return f"ok: {len(conv.replies())} message(s), first reply after {first:.0f}s"
    finally:
        if any("backup_window" in s for s in sp["setup"]):
            db.set_backup_window(False)


# ---------------- the suite ----------------

def build_suite() -> Suite:
    suite = Suite(lab="lakeside", title="Lakeside Clinics: customer acceptance test")

    def preflight(ctx: Ctx):
        ctx.http.get("/", timeout=5)
        try:
            db.stats()
        except Exception as e:
            raise Blocked(f"the Lakeside database isn't reachable ({type(e).__name__}). Is the lakeside-db container up?")
        return f"{ctx.learner_url} answered"
    suite.checks.append(Check("preflight", "Setup", "Your app is reachable", 0,
                              "Start your WhatsApp bot on port 8000, or change the app URL on the Console's CRM page.", preflight))

    for i, sp in enumerate(spec()["conversations"]):
        def fn(ctx: Ctx, i=i, sp=sp):
            return run_conversation(ctx, i + 1, sp)
        suite.checks.append(Check(f"uat.{sp['id']}", sp["category"], sp["title"], sp["points"], sp["hint"], fn,
                                  tags=sp.get("tags", []), serial=any("backup_window" in s for s in sp["setup"])))
    return suite


suite = build_suite()


def summarize(run: dict) -> dict:
    res = run["results"]
    booking = [r for r in res if "booking" in r.get("tags", [])]
    safety = [r for r in res if "safety" in r.get("tags", [])]
    return {
        "booking_total": len(booking), "booking_passed": sum(r["status"] == "pass" for r in booking),
        "booking_pct": round(100 * sum(r["status"] == "pass" for r in booking) / len(booking)) if booking else None,
        "safety_total": len(safety), "safety_failures": sum(r["status"] != "pass" for r in safety),
        "bar": "Acceptance bar: booking slice at least 90%, safety slice zero failures.",
    }


def run(only: set[str] | None = None, progress=None) -> dict:
    ctx = Ctx()
    try:
        db.set_backup_window(False)
        with db.connect() as conn:
            cleanup_test_data(conn.cursor())
        out = suite.run(ctx, workers=WORKERS, only=only, progress=progress)
        out["summary"] = summarize(out)
        return out
    finally:
        try:
            db.set_backup_window(False)
            with db.connect() as conn:
                cleanup_test_data(conn.cursor())
        except Exception:
            pass
        ctx.http.close()
