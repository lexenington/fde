"""Savanna Microfinance's documents: a 140-page credit policy, dated circulars that supersede parts of it,
and a regional manager's WhatsApp export. Generated deterministically from content/savanna/rules.json, so the
documents and the answer key can never disagree.
"""

import json
import random
import re
from datetime import date

from fpdf import FPDF

from . import config

POLICY_NAME = "Credit-Policy-Manual-v7.pdf"
TARGET_PAGES = 140


def content() -> dict:
    return json.loads((config.CONTENT_DIR / "savanna" / "rules.json").read_text(encoding="utf-8"))


def whatsapp_lines() -> list[list[str]]:
    return json.loads((config.CONTENT_DIR / "savanna" / "whatsapp.json").read_text(encoding="utf-8"))["lines"]


def circulars() -> list[dict]:
    """Every circular implied by the rules' amendment histories, in number order."""
    out = []
    for r in content()["rules"]:
        for h in r["history"]:
            out.append({**h, "rule": r["id"], "section": r["section"], "title": r["title"]})
    return sorted(out, key=lambda c: c["circular"])


def effective_value_circular(rule: dict, as_of: str) -> dict | None:
    """The last circular in force on `as_of` for this rule, or None if the base text still applies."""
    live = [h for h in rule["history"] if h["effective"] <= as_of]
    return max(live, key=lambda h: h["effective"]) if live else None


# ---------- filler: realistic, number-free policy prose ----------

SUBJECTS = ["The loan officer", "The branch manager", "The credit committee", "The branch cashier", "The regional office", "Each member",
            "The group leader", "The operations supervisor", "The compliance officer", "The branch accountant", "The field agent"]
ACTIONS = ["shall record every visit in the field diary", "shall update the member register on the same working day",
           "shall keep the original documents in the locked cabinet", "shall confirm the details with the member in person",
           "shall report any irregularity to the supervisor without delay", "shall countersign the voucher before any payment is made",
           "shall maintain a complete and legible file for each member", "shall explain the terms in a language the member understands",
           "shall file the monthly return with the regional office", "shall not accept any gift or favour from a borrower",
           "shall treat every member with courtesy and respect", "shall check the identity of the person collecting a payment",
           "shall reconcile the cash book with the till at the close of business", "shall escalate disputes to the next level of authority"]
CONTEXT = ["in accordance with this Manual", "as required by the Bank of Ghana guidelines", "and sign and date the entry",
           "so that the record is available for audit", "and inform the member of the outcome", "using the approved form",
           "and note the reason for any exception", "before the end of the working day", "and keep a copy on the branch file"]
BRIDGES = ["Where a document is missing, the officer shall obtain it before proceeding.", "Exceptions shall be recorded and reported at the next review.",
           "These requirements apply to every branch and to every product unless stated otherwise.", "Staff are reminded that this section forms part of the terms of their employment.",
           "Questions on interpretation shall be referred to the Risk and Compliance department.", "The Internal Audit department may inspect these records at any time.",
           "No officer may waive a requirement in this section without written authority."]
PARTS = {1: "General provisions", 2: "Eligibility and know-your-customer", 3: "Governance and approvals", 4: "Individual loans", 5: "Pricing and fees",
         6: "Group loans", 7: "Emergency loans", 8: "Collections and arrears", 9: "Disbursement and cash handling", 10: "Records and data protection",
         11: "Branch operations", 12: "Staff conduct", 13: "Appendices and forms"}
FILLER_TITLES = ["Purpose and scope", "Responsibilities", "Documentation", "Reporting", "Record keeping", "Review and audit", "Exceptions", "Training",
                 "Member communication", "Complaints", "Supervision", "Branch procedures", "Roles and escalation", "Definitions"]


def _para(rnd: random.Random) -> str:
    sents = []
    for _ in range(rnd.randint(4, 6)):
        if rnd.random() < 0.28:
            sents.append(rnd.choice(BRIDGES))
        else:
            sents.append(f"{rnd.choice(SUBJECTS)} {rnd.choice(ACTIONS)} {rnd.choice(CONTEXT)}.")
    return " ".join(sents)


class Doc(FPDF):
    def __init__(self, title: str):
        super().__init__()
        self.doc_title = title
        self.set_auto_page_break(True, margin=18)

    def header(self):
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 6, f"Savanna Microfinance Ltd  |  {self.doc_title}", align="L")
        self.ln(8)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")


def _ascii(t: str) -> str:
    return t.encode("latin-1", "replace").decode("latin-1")


def _subsections(rules: list[dict]) -> dict[int, dict[int, dict[int, dict]]]:
    tree: dict = {}
    for r in rules:
        p, s, i = (int(x) for x in r["section"].split("."))
        tree.setdefault(p, {}).setdefault(s, {})[i] = r
    return tree


def build_policy(path, filler_per_item: int, extra_items: int = 0) -> int:
    """`extra_items` of the items get one more paragraph: a fine control over the page count."""
    rules = content()["rules"]
    tree = _subsections(rules)
    rnd = random.Random(7)
    counter = [0]
    pdf = Doc("Credit Policy Manual, Version 7")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.ln(50)
    pdf.multi_cell(0, 12, new_x='LMARGIN', new_y='NEXT', text="SAVANNA MICROFINANCE LTD", align="C")
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 12, new_x='LMARGIN', new_y='NEXT', text="CREDIT POLICY MANUAL", align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.ln(6)
    pdf.multi_cell(0, 8, new_x='LMARGIN', new_y='NEXT', text="Version 7\nIssued to all branches\nAmendments are made by numbered Circulars. Where a Circular amends a section, the Circular prevails.", align="C")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Contents", new_x='LMARGIN', new_y='NEXT')
    pdf.set_font("Helvetica", "", 10)
    for p, name in PARTS.items():
        pdf.cell(0, 6, f"Part {p}.  {name}", new_x='LMARGIN', new_y='NEXT')
    for p, name in PARTS.items():
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, _ascii(f"Part {p}.  {name}"), new_x='LMARGIN', new_y='NEXT')
        subs = tree.get(p, {})
        n_subs = max(max(subs, default=0), 6)
        for s in range(1, n_subs + 1):
            pdf.set_font("Helvetica", "B", 12)
            pdf.ln(2)
            pdf.cell(0, 8, _ascii(f"{p}.{s}  {FILLER_TITLES[(p + s) % len(FILLER_TITLES)]}"), new_x='LMARGIN', new_y='NEXT')
            items = subs.get(s, {})
            n_items = max(max(items, default=0), 3)
            for i in range(1, n_items + 1):
                r = items.get(i)
                pdf.set_font("Helvetica", "B", 10)
                title = r["title"] if r else FILLER_TITLES[(p * 3 + s + i) % len(FILLER_TITLES)]
                pdf.cell(0, 6, _ascii(f"{p}.{s}.{i}  {title}"), new_x='LMARGIN', new_y='NEXT')
                pdf.set_font("Helvetica", "", 10)
                if r:
                    pdf.multi_cell(0, 5, new_x='LMARGIN', new_y='NEXT', text=_ascii(r["base"]))
                    pdf.ln(1)
                counter[0] += 1
                for _ in range(filler_per_item + (1 if counter[0] <= extra_items else 0)):
                    pdf.multi_cell(0, 5, new_x='LMARGIN', new_y='NEXT', text=_ascii(_para(rnd)))
                    pdf.ln(1)
    pdf.output(str(path))
    return pdf.page_no()


def build_circular(path, c: dict):
    pdf = Doc(f"Circular {c['circular']}")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"CIRCULAR No. {c['circular']}", new_x='LMARGIN', new_y='NEXT')
    pdf.set_font("Helvetica", "", 10)
    issued = date.fromisoformat(c["issued"])
    eff = date.fromisoformat(c["effective"])
    pdf.multi_cell(0, 6, new_x='LMARGIN', new_y='NEXT', text=_ascii(
        f"To: All Branch Managers and Credit Officers\nFrom: Head Office, Credit and Risk\nDate: {issued.day} {issued.strftime('%B %Y')}\n"
        f"Effective: {eff.day} {eff.strftime('%B %Y')}\nSubject: {c['title']} (Section {c['section']})"))
    pdf.ln(4)
    body = (f"Section {c['section']} of the Credit Policy Manual, Version 7 ({c['title']}) is amended as follows.\n\n{c['text']}\n\n"
            + (f"This circular supersedes Circular {c['supersedes']} on this point.\n\n" if c.get("supersedes") and "supersedes" not in c["text"] else "")
            + "All other provisions of the Manual remain in force. Branch managers shall brief their officers and acknowledge receipt.")
    pdf.multi_cell(0, 6, new_x='LMARGIN', new_y='NEXT', text=_ascii(body))
    pdf.output(str(path))


def whatsapp_text() -> str:
    out = []
    for d, t, who, msg in whatsapp_lines():
        y, m, dd = d.split("-")
        out.append(f"[{dd}/{m}/{y}, {t}:00] {who}: {msg}")
    return "\n".join(out) + "\n"


def write_documents(share_dir) -> list[dict]:
    """Write the policy, the circulars and the WhatsApp export. Returns a manifest for the Console."""
    from pathlib import Path
    share = Path(share_dir)
    (share / "circulars").mkdir(parents=True, exist_ok=True)
    (share / "whatsapp").mkdir(parents=True, exist_ok=True)
    # aim for 140 pages: find the fill level just below the target, then add one paragraph to as many items as needed
    k, lo = 1, build_policy(share / POLICY_NAME, 1)
    while True:
        hi = build_policy(share / POLICY_NAME, k + 1)
        if hi > TARGET_PAGES or k > 12:
            break
        k, lo = k + 1, hi
    n_items = sum(max(max(it, default=0), 3) for p_ in PARTS for it in (_subsections(content()["rules"]).get(p_, {}).get(s_, {}) for s_ in range(1, 7)))
    extra = max(0, min(n_items, round(n_items * (TARGET_PAGES - lo) / max(hi - lo, 1))))
    pages = build_policy(share / POLICY_NAME, k, extra)
    manifest = [{"path": POLICY_NAME, "title": "Credit Policy Manual, Version 7", "kind": "policy", "pages": pages}]
    for c in circulars():
        name = f"circulars/Circular-{c['circular'].replace('/', '-')}.pdf"
        build_circular(share / name, c)
        manifest.append({"path": name, "title": f"Circular {c['circular']}", "kind": "circular", "pages": 1})
    (share / "whatsapp" / "Northern-Region-Credit-Officers.txt").write_text(whatsapp_text(), encoding="utf-8")
    manifest.append({"path": "whatsapp/Northern-Region-Credit-Officers.txt", "title": "WhatsApp group export, Northern Region credit officers", "kind": "whatsapp", "pages": None})
    return manifest


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9.%]+", " ", text.lower()).strip()
