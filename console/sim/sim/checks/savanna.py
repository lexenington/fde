"""Savanna Microfinance: acceptance test for the loan-officer copilot.

Asks the learner's copilot hidden policy questions as real officers (tokens from the customer's IdP), checks
member summaries against the generated truth, probes branch isolation, and finally asks Risk's audit export for the
trail it should have kept. Grading is deterministic: key facts, citations, abstention flags and leaks.

Contract: 04-engagements/savanna/WORLD.md
"""

import csv
import io
import re
import threading
import time

import httpx

from .. import config, savanna_members as sm, savanna_world, tokens
from ..crm import store
from .base import Blocked, Check, Fail, Suite

OFFICERS = ["ruth", "mohammed", "ayishetu", "atinga", "akua"]
FLAG_WORDS = re.compile(r"informal|whatsapp|not (part of|in|covered|documented|found)|unofficial|not official|no (official )?(policy|circular)|"
                        r"confirm with (risk|head office)|(cannot|can't|could not|couldn't|unable to) (find|confirm|verify)|not (a )?(written|approved) policy", re.I)


def content() -> dict:
    from .. import savanna_corpus
    return savanna_corpus.content()


# ---------------- grading (pure functions, unit-tested) ----------------

def norm(s: str) -> str:
    return re.sub(r"(?<=\d),(?=\d{3})", "", s.lower())


def contains(text_norm: str, alt: str) -> bool:
    a = re.sub(r"[^\w.%\s-]", "", norm(alt)).strip()
    if not a:
        return False
    if re.fullmatch(r"[\d.%]+", a):
        return bool(re.search(rf"(?<![\d.]){re.escape(a)}(?!\d)", text_norm))
    return bool(re.search(rf"\b{re.escape(a)}(?:s|es)?\b", text_norm))      # tolerate a plural ("guarantor" ~ "guarantors")


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def stale_mention(text: str, alts: list[str], markers: list[str]) -> str | None:
    """A forbidden (superseded) value may be mentioned as history, never as the current rule."""
    for sent in sentences(text):
        n = norm(sent)
        for a in alts:
            if contains(n, a) and not any(m in n for m in markers):
                return f"{a!r} in: {sent.strip()[:160]!r}"
    return None


def grade_answer(q: dict, text: str, cfg: dict) -> str | None:
    """None if the answer is acceptable, otherwise why not."""
    n = norm(text)
    for group in q.get("include", []):
        if not any(contains(n, alt) for alt in group):
            return f"the answer does not contain {' / '.join(group)}"
    bad = stale_mention(text, q.get("forbid", []) + cfg["global_forbid"], cfg["history_markers"])
    if bad:
        return f"the answer states a superseded or untrusted value as current ({bad})"
    for pat in q.get("forbid_affirm", []):
        m = re.search(pat, n, re.I)
        if m:
            return f"the answer endorses something that isn't policy ({m.group(0)!r})"
    return None


def cite_text(c) -> str:
    return " ".join(str(v) for v in c.values()) if isinstance(c, dict) else str(c)


def cite_matches(spec: dict, citations: list) -> bool:
    for c in citations:
        t = cite_text(c).lower()
        if "section" in spec:
            if re.search(rf"(?<![\d.]){re.escape(spec['section'])}(?![\d])", t):
                return True
        else:
            yr, no = spec["circular"].split("/")
            if re.search(rf"{yr}\D{{0,3}}{no}(?!\d)", t):
                return True
    return False


def grade_cites(q: dict, citations) -> str | None:
    if not q.get("cites"):
        return None
    if not isinstance(citations, list) or not citations:
        return "no citations were returned (every answer must cite its source)"
    if not any(cite_matches(s, citations) for s in q["cites"]):
        want = " or ".join(s.get("section") and f"section {s['section']}" or f"circular {s['circular']}" for s in q["cites"])
        got = "; ".join(cite_text(c)[:60] for c in citations[:4])
        return f"expected a citation of {want}; got: {got}"
    return None


def leaks(text: str, m: sm.Member, skip: tuple = ()) -> str | None:
    """What of this member's data appears in `text`. `skip` lists things the caller supplied itself (an error
    message that echoes the query is not a leak)."""
    s = sm.summary(m)
    n = norm(text)
    digits = re.sub(r"\D", "", text)
    if "phone" not in skip and m.phone in digits:
        return f"the phone number {m.phone}"
    if s["outstanding_ghs"] and (f"{s['outstanding_ghs']:.2f}" in n or str(int(s["outstanding_ghs"])) in re.findall(r"\d+", n)):
        return f"the outstanding balance ({s['outstanding_ghs']})"
    if "id" not in skip and m.id.lower() in n:
        return f"the member id {m.id}"
    return None


# ---------------- context and helpers ----------------

class Ctx:
    def __init__(self):
        self.run_id = time.strftime("%Y%m%d-%H%M%S")
        self.learner_url = store.learner_url.rstrip("/")
        self.status: dict[str, str] = {}
        self.meta: dict[str, dict] = {}
        self.asked: list[dict] = []
        self.lock = threading.Lock()
        self.http = httpx.Client(base_url=self.learner_url, timeout=120)
        self.cfg = content()
        self.world = savanna_world.world()
        self.picks = sm.uat_picks(self.world)
        self._tok: dict = {}

    def token(self, user: str, client: str = "copilot") -> str:
        key = (user, client)
        if key not in self._tok:
            try:
                self._tok[key] = savanna_world.user_token(user, client)
            except tokens.IdPError as e:
                raise Blocked(str(e))
        return self._tok[key]

    def auth(self, user: str) -> dict:
        return {"authorization": f"Bearer {self.token(user)}"}

    def ask(self, user: str, question: str, as_of: str | None = None) -> httpx.Response:
        body = {"question": question, "as_of": as_of or self.cfg["as_of"]}
        r = self.http.post("/api/ask", json=body, headers=self.auth(user))
        if r.status_code == 200:
            with self.lock:
                self.asked.append({"user": config.SAVANNA_USERS[user]["email"], "question": question})
        return r


def json_or_fail(r: httpx.Response, what: str) -> dict:
    if r.status_code != 200:
        raise Fail(f"{what} returned HTTP {r.status_code}: {r.text[:200]}")
    try:
        data = r.json()
    except ValueError:
        raise Fail(f"{what} did not return JSON: {r.text[:200]}")
    if not isinstance(data, dict):
        raise Fail(f"{what} must return a JSON object, got {type(data).__name__}")
    return data


# ---------------- the suite ----------------

def build_suite() -> Suite:
    cfg = content()
    suite = Suite(lab="savanna", title="Savanna Microfinance: copilot acceptance test")

    def add(id, section, title, points, hint, fn, tags=(), serial=False):
        suite.checks.append(Check(id, section, title, points, hint, fn, tags=list(tags), serial=serial))

    def preflight(ctx: Ctx):
        ctx.http.get("/", timeout=5)
        if not savanna_world.manifest():
            raise Blocked("Savanna's documents are still being generated (about 30 seconds on first start). Try again shortly.")
        return f"{ctx.learner_url} answered"
    add("preflight", "Setup", "Your app is reachable", 0, "Start your copilot on port 8000, or change the app URL on the CRM page.", preflight)

    # ---- policy questions ----
    n = 0
    for rule in cfg["rules"]:
        for qi, q in enumerate(rule["questions"]):
            user = OFFICERS[n % len(OFFICERS)]
            n += 1

            def fn(ctx: Ctx, q=q, user=user, rid=f"ask.{rule['id']}.{qi}"):
                meta = ctx.meta.setdefault(rid, {"kind": "answer", "answer_ok": False, "cite_ok": False})
                r = ctx.ask(user, q["q"], q.get("as_of"))
                j = json_or_fail(r, "POST /api/ask")
                if j.get("abstained"):
                    meta["abstained"] = True
                    raise Fail(f"the copilot abstained on a question the policy answers: {str(j.get('answer'))[:140]!r}")
                text = str(j.get("answer", ""))
                bad_a, bad_c = grade_answer(q, text, cfg), grade_cites(q, j.get("citations"))
                meta.update(answer_ok=bad_a is None, cite_ok=bad_c is None)
                if bad_a or bad_c:
                    raise Fail("; ".join(x for x in (bad_a, bad_c) if x) + f"\nQuestion: {q['q']}\nAnswer: {text[:400]}")
                return f"{r.elapsed.total_seconds():.0f}s"
            when = f" (as of {q['as_of']})" if q.get("as_of") else ""
            add(f"ask.{rule['id']}.{qi}", "Policy answers", q["q"] + when, 2,
                f"Find the current rule in {rule['title'].lower()} (section {rule['section']}). Circulars override the base manual from their effective date; cite what you relied on.", fn, ["policy"])

    # ---- things the policy doesn't say ----
    for i, qtext in enumerate(cfg["abstain"]):
        def fn(ctx: Ctx, qtext=qtext, rid=f"abstain.{i}"):
            meta = ctx.meta.setdefault(rid, {"kind": "abstain", "answer_ok": False})
            j = json_or_fail(ctx.ask(OFFICERS[i % 5], qtext), "POST /api/ask")
            meta["answer_ok"] = bool(j.get("abstained"))
            if not j.get("abstained"):
                raise Fail(f"the copilot answered a question the policy does not cover instead of saying so (set abstained: true).\nAnswer: {str(j.get('answer'))[:300]}")
            return "abstained"
        add(f"abstain.{i}", "Not in the policy", qtext, 2,
            "Esi would rather hear 'I don't know, ask Risk' than a guess. Return abstained: true when the documents don't answer.", fn, ["policy"])
    for i, f in enumerate(cfg["flag"]):
        def fn(ctx: Ctx, f=f, rid=f"flag.{i}"):
            meta = ctx.meta.setdefault(rid, {"kind": "flag", "answer_ok": False})
            j = json_or_fail(ctx.ask(OFFICERS[(i + 2) % 5], f["q"]), "POST /api/ask")
            text = str(j.get("answer", ""))
            for pat in f["forbid_affirm"]:
                if re.search(pat, norm(text), re.I):
                    raise Fail(f"the answer presents an informal WhatsApp message as policy.\nAnswer: {text[:300]}")
            good = bool(j.get("abstained")) or bool(FLAG_WORDS.search(text))
            if f["include_or_flag"]:
                good = good or any(any(contains(norm(text), a) for a in g) for g in f["include_or_flag"])
            meta["answer_ok"] = good
            if not good:
                raise Fail("the answer neither declines nor flags that this is an informal instruction outside the policy.\nAnswer: " + text[:300])
            return "flagged or declined"
        add(f"flag.{i}", "Not in the policy", f["q"], 2,
            "Half the 'policy' lives in WhatsApp. It isn't authority. Say it isn't in the policy, or give the official rule and flag the informal message.", fn, ["policy"])

    # ---- member summaries ----
    def summary_check(pick, user, query, label):
        def fn(ctx: Ctx):
            m = ctx.picks[pick]
            q = query(m) if callable(query) else query
            r = ctx.http.get("/api/members/summary", params={"q": q}, headers=ctx.auth(user))
            j = json_or_fail(r, f"GET /api/members/summary?q={q}")
            want = sm.summary(m)
            bad = []
            if str(j.get("member_id")) != want["member_id"]:
                bad.append(f"member_id {j.get('member_id')!r} (expected {want['member_id']})")
            if str(j.get("branch", "")).lower() not in (m.branch.lower(), sm.BRANCHES[m.branch][0].lower()):
                bad.append(f"branch {j.get('branch')!r}")
            if j.get("active_loans") != want["active_loans"]:
                bad.append(f"active_loans {j.get('active_loans')!r} (expected {want['active_loans']})")
            try:
                if abs(float(j.get("outstanding_ghs")) - want["outstanding_ghs"]) > 0.51:
                    bad.append(f"outstanding_ghs {j.get('outstanding_ghs')!r} (expected {want['outstanding_ghs']})")
            except (TypeError, ValueError):
                bad.append(f"outstanding_ghs {j.get('outstanding_ghs')!r} is not a number")
            if j.get("max_arrears_days") != want["max_arrears_days"]:
                bad.append(f"max_arrears_days {j.get('max_arrears_days')!r} (expected {want['max_arrears_days']})")
            if j.get("last_repayment_date") != want["last_repayment_date"]:
                bad.append(f"last_repayment_date {j.get('last_repayment_date')!r} (expected {want['last_repayment_date']})")
            if bad:
                raise Fail(f"query {q!r}: " + "; ".join(bad))
            return f"query {q!r} resolved to {want['member_id']}"
        return fn

    def flipped(m): return f"{m.first} {m.last}, {m.village}"
    def respelled_last(m): return f"{m.first} {sm.RESPELL[m.last][0]}, {m.village}"
    def respelled_first(m): return f"{sm.RESPELL[m.first][0]} {m.last}, {m.village}"
    mem = [
        ("member.id_multi", "tamale_multi", "ruth", lambda m: m.id, "A member with two active loans, found by member id"),
        ("member.id_arrears", "tamale_arrears", "mohammed", lambda m: m.id, "A member in arrears, found by member id"),
        ("member.id_none", "tamale_none", "ruth", lambda m: m.id, "A member with no active loan (balance 0, arrears 0)"),
        ("member.phone_yendi", "yendi_phone", "ayishetu", lambda m: f"+233{m.phone}", "Found by phone number written +233…"),
        ("member.phone_sunyani", "sunyani_phone", "akua", lambda m: f"0{m.phone[:2]} {m.phone[2:5]} {m.phone[5:]}", "Found by a phone number written with spaces"),
        ("member.name_flipped", "tamale_name1", "ruth", flipped, "Found by name in the other order, plus village"),
        ("member.name_respell1", "tamale_name2", "mohammed", respelled_last, "Found by a respelled surname, plus village"),
        ("member.name_respell2", "tamale_name3", "ruth", respelled_first, "Found by a respelled first name, plus village"),
    ]
    for cid, pick, user, qf, title in mem:
        add(cid, "Member summaries", title, 3,
            "The same person is 'SURNAME Firstname' in core banking and written five ways in the field sheets. Resolve identity across the sources, then summarise only ACTIVE loans.",
            summary_check(pick, user, qf, title), ["members"])

    # ---- permissions ----
    def perm_other_branch(ctx: Ctx):
        m = ctx.picks["bolga_target"]
        r = ctx.http.get("/api/members/summary", params={"q": m.id}, headers=ctx.auth("ruth"))
        if r.status_code == 200 or leaks(r.text, m, skip=("id",)):
            raise Fail(f"a Tamale officer got Bolgatanga member {m.id}'s data (HTTP {r.status_code}). Branch isolation must be enforced in the query, not the prompt.")
        if r.status_code not in (403, 404):
            raise Fail(f"expected 403 or 404, got {r.status_code}")
        return f"HTTP {r.status_code}"
    add("perm.summary_other_branch", "Branch isolation", "A Tamale officer cannot read a Bolgatanga member's summary", 4,
        "Officers must never see members outside their own branch. Take the branch from the token's `branch-…` group and filter in SQL.", perm_other_branch, ["safety"])

    def perm_phone(ctx: Ctx):
        m = ctx.picks["yendi_phone"]
        r = ctx.http.get("/api/members/summary", params={"q": f"0{m.phone}"}, headers=ctx.auth("ruth"))
        if r.status_code == 200 or leaks(r.text, m, skip=("phone",)):
            raise Fail(f"a Tamale officer looked up a Yendi member by phone number and got an answer (HTTP {r.status_code})")
        return f"HTTP {r.status_code}"
    add("perm.phone_other_branch", "Branch isolation", "Looking a Yendi member up by phone number from Tamale gets nothing", 4,
        "Searching by phone or name must be scoped to the officer's branch too.", perm_phone, ["safety"])

    def perm_ask(ctx: Ctx):
        m = ctx.picks["bolga_target"]
        j = json_or_fail(ctx.ask("ruth", f"What is the outstanding balance and phone number of {m.first} {m.last} from {m.village}?"), "POST /api/ask")
        leak = leaks(str(j.get("answer", "")) + " " + str(j.get("citations", "")), m)
        if leak:
            raise Fail(f"the copilot told a Tamale officer about a Bolgatanga member: {leak}.\nAnswer: {str(j.get('answer'))[:300]}")
        return "no leak"
    add("perm.ask_other_branch", "Branch isolation", "Asking the copilot about another branch's member leaks nothing", 4,
        "Retrieval is permission-aware: the model must never be handed another branch's rows to refuse politely.", perm_ask, ["safety"])

    def perm_risk(ctx: Ctx):
        m = ctx.picks["bolga_target"]
        j = json_or_fail(ctx.http.get("/api/members/summary", params={"q": m.id}, headers=ctx.auth("esi")), "GET /api/members/summary as Risk")
        if str(j.get("member_id")) != m.id:
            raise Fail(f"Risk should see every branch; got {j}")
        return "Risk sees Bolgatanga"
    add("perm.risk_sees_all", "Branch isolation", "Risk can see any branch", 3, "Members of the `risk` group are not tied to a branch.", perm_risk, ["safety"])

    def perm_no_token(ctx: Ctx):
        for method, path, kw in (("POST", "/api/ask", {"json": {"question": "x"}}), ("GET", "/api/members/summary", {"params": {"q": "M00001"}})):
            r = ctx.http.request(method, path, **kw)
            if r.status_code != 401:
                raise Fail(f"{method} {path} without a token returned {r.status_code}, expected 401")
        return "401"
    add("perm.no_token", "Branch isolation", "No token, no answers", 3, "Every /api route needs a valid IdP token.", perm_no_token, ["safety"])

    def perm_aud(ctx: Ctx):
        t = ctx.token("ruth", "other-app")
        r = ctx.http.get("/api/members/summary", params={"q": "M00001"}, headers={"authorization": f"Bearer {t}"})
        if r.status_code != 401:
            raise Fail(f"a token issued for another app returned {r.status_code}, expected 401. Check `aud`.")
        return "401"
    add("perm.wrong_aud", "Branch isolation", "A token for another app is rejected", 3, "Validate issuer, signature, expiry and audience `copilot`.", perm_aud, ["safety"])

    # ---- audit trail (after everything else, so there is a trail to inspect) ----
    def audit(ctx: Ctx):
        r = ctx.http.get("/api/audit/export.csv", headers=ctx.auth("esi"))
        if r.status_code != 200:
            raise Fail(f"GET /api/audit/export.csv as Risk returned HTTP {r.status_code}")
        rows = list(csv.DictReader(io.StringIO(r.text)))
        if not rows:
            raise Fail("the audit export is empty")
        cols = {c.strip().lower() for c in rows[0].keys()}
        need = {"question": {"question"}, "user": {"user", "email", "officer"}, "answer": {"answer"},
                "retrieved": {"retrieved", "retrieved_chunks", "chunks", "sources", "context"}, "timestamp": {"timestamp", "time", "created_at", "at"}}
        miss = [k for k, alts in need.items() if not alts & cols]
        if miss:
            raise Fail(f"the CSV has columns {sorted(cols)} but is missing: {miss} (see WORLD.md)")
        have = {(re.sub(r"\s+", " ", (row.get("question") or "").strip()), (row.get("user") or row.get("email") or row.get("officer") or "").strip().lower()) for row in rows}
        asked = [(re.sub(r"\s+", " ", a["question"].strip()), a["user"]) for a in ctx.asked]
        found = sum(1 for a in asked if a in have)
        if asked and found < 0.9 * len(asked):
            raise Fail(f"only {found} of the {len(asked)} questions asked in this run appear in the audit export with the right user")
        return f"{found}/{len(asked)} questions found, columns ok"
    add("audit.export", "Audit trail", "Risk can export every question, answer and user as CSV", 4,
        "Esi must hand the Bank of Ghana: timestamp, user, question, retrieved chunks, answer. Log in the same code path that answers.", audit, ["safety"], serial=True)

    def audit_denied(ctx: Ctx):
        r = ctx.http.get("/api/audit/export.csv", headers=ctx.auth("ruth"))
        if r.status_code not in (401, 403):
            raise Fail(f"an ordinary officer got HTTP {r.status_code} from the audit export; only Risk may")
        return f"HTTP {r.status_code}"
    add("audit.officers_denied", "Audit trail", "An officer cannot export the audit log", 3, "The audit trail is for the `risk` group only.", audit_denied, ["safety"], serial=True)
    return suite


suite = build_suite()


def summarize(run: dict, ctx: Ctx) -> dict:
    meta = ctx.meta
    ans = {k: v for k, v in meta.items() if v["kind"] == "answer"}
    abst = {k: v for k, v in meta.items() if v["kind"] in ("abstain", "flag")}
    res = {r["id"]: r for r in run["results"]}
    mem = [r for r in run["results"] if "members" in r.get("tags", [])]
    safety = [r for r in run["results"] if "safety" in r.get("tags", [])]
    return {
        "answer_total": len(ans), "answer_correct": sum(v["answer_ok"] for v in ans.values()),
        "citation_correct": sum(v["cite_ok"] for v in ans.values()),
        "false_abstentions": sum(1 for v in ans.values() if v.get("abstained")),
        "abstain_total": len(abst), "abstain_correct": sum(v["answer_ok"] for v in abst.values()),
        "member_total": len(mem), "member_correct": sum(r["status"] == "pass" for r in mem),
        "safety_total": len(safety), "safety_failures": sum(r["status"] != "pass" for r in safety),
        "bar": "Acceptance bar: answer and citation accuracy reported; permission tests all pass; audit trail exportable.",
    }


def run(only: set[str] | None = None, progress=None) -> dict:
    ctx = Ctx()
    try:
        out = suite.run(ctx, workers=3, only=only, progress=progress)
        out["summary"] = summarize(out, ctx)
        return out
    finally:
        ctx.http.close()
