"""Savanna Microfinance's members, loans and repayments, as three sources that disagree:

1. the core-banking nightly export (SURNAME Firstname, one phone format, official branch codes)
2. the officers' field sheets (names the way people write them, five spellings, phones missing or wrong)
3. the regional manager's WhatsApp messages (names and numbers in free text)

The truth is generated first and the sources are derived from it, so the acceptance test can check
member summaries exactly. Deterministic: the same seed gives the same people.
"""

import csv
import io
import random
from dataclasses import dataclass, field
from datetime import date, timedelta

AS_OF = date(2026, 10, 6)
BRANCHES = {   # code: (name, region)
    "TAMALE-C": ("Tamale Central", "Northern"), "YENDI": ("Yendi", "Northern"),
    "BOLGA": ("Bolgatanga", "Upper East"), "BAWKU": ("Bawku", "Upper East"), "NAVRONGO": ("Navrongo", "Upper East"),
    "SUNYANI": ("Sunyani", "Bono"), "TECHIMAN": ("Techiman", "Bono"), "BEREKUM": ("Berekum", "Bono"),
}
FIELD_SHEET_BRANCHES = ["TAMALE-C", "YENDI", "BOLGA", "SUNYANI"]
VILLAGES = {
    "Northern": ["Gbullung", "Kpalsi", "Nyankpala", "Gushegu", "Zangbalun", "Kumbungu", "Sagnarigu", "Tolon", "Savelugu", "Bimbilla"],
    "Upper East": ["Zuarungu", "Sumbrungu", "Bongo", "Garu", "Tempane", "Pusiga", "Sandema", "Paga", "Zebilla", "Binduri"],
    "Bono": ["Dormaa", "Abesim", "Fiapre", "Nsoatre", "Tanoso", "Kwatire", "Odumase", "Kenyasi", "Ahenkro", "Chiraa"],
}
NAMES = {   # region: (first names, surnames)
    "Northern": (["Ruth", "Memunatu", "Fatima", "Ibrahim", "Salifu", "Abdul", "Zainab", "Mariama", "Alhassan", "Haruna", "Rashida", "Issah", "Sulemana", "Hawa"],
                 ["Alhassan", "Mohammed", "Abdulai", "Iddrisu", "Fuseini", "Yakubu", "Zakaria", "Mumuni", "Issahaku", "Seidu", "Abukari", "Wumbei"]),
    "Upper East": (["Atinga", "Akolbire", "Apoka", "Adongo", "Azure", "Ayishetu", "Ayinbora", "Abugri", "Akanbong", "Adwoa", "Mary", "Rebecca"],
                   ["Ayamga", "Atinga", "Akolgo", "Anaba", "Apana", "Azumah", "Bukari", "Atuguba", "Ayine", "Akurugu", "Adongo", "Abuga"]),
    "Bono": (["Kwame", "Ama", "Yaw", "Akua", "Kofi", "Abena", "Kwabena", "Adwoa", "Kwaku", "Afia", "Yaa", "Kojo"],
             ["Boateng", "Mensah", "Owusu", "Asante", "Agyei", "Appiah", "Darko", "Ofori", "Nkansah", "Frimpong", "Badu", "Amoah"]),
}
RESPELL = {  # canonical -> other ways officers write it
    "Mohammed": ["Mohamed", "Muhammed", "Mohammad"], "Alhassan": ["Alhasan", "Alhassane", "Alasan"], "Abdulai": ["Abdulahi", "Abdulay"],
    "Iddrisu": ["Idrisu", "Idriss", "Iddrissu"], "Fuseini": ["Fusheini", "Fuseni"], "Yakubu": ["Yakubo", "Yaqub"],
    "Issahaku": ["Issaka", "Isahaku"], "Seidu": ["Seidou", "Sidu"], "Ayamga": ["Ayanga", "Ayamba"], "Atinga": ["Atiga", "Atingah"],
    "Boateng": ["Boatey", "Boatang"], "Mensah": ["Mensa", "Mensar"], "Asante": ["Ashante", "Asanti"], "Ofori": ["Offori", "Ofori-Atta"],
    "Zakaria": ["Zakariah", "Zacharia"], "Mumuni": ["Mumuney", "Momuni"], "Fatima": ["Fatimah", "Fatma"], "Memunatu": ["Memuna", "Mamunatu"],
}


@dataclass
class Member:
    id: str
    branch: str
    first: str
    last: str
    phone: str            # nine digits
    village: str
    loans: list = field(default_factory=list)


def core_name(m: Member) -> str:
    return f"{m.last.upper()} {m.first}"


def generate(seed: int = 2026, per_branch: int = 62) -> dict:
    rnd = random.Random(seed)
    members: list[Member] = []
    used = set()
    n = 0
    for code, (_, region) in BRANCHES.items():
        firsts, lasts = NAMES[region]
        for _ in range(per_branch):
            n += 1
            phone = rnd.choice(["24", "54", "55", "20", "50", "27", "26", "59"]) + "".join(rnd.choice("0123456789") for _ in range(7))
            while phone in used:
                phone = phone[:-1] + rnd.choice("0123456789")
            used.add(phone)
            members.append(Member(f"M{n:05d}", code, rnd.choice(firsts), rnd.choice(lasts), phone, rnd.choice(VILLAGES[region])))
    loans, repayments = [], []
    ln = 0
    for m in members:
        k = rnd.choices([1, 2, 3], [0.5, 0.35, 0.15])[0]
        start = AS_OF - timedelta(days=rnd.randint(700, 900))
        for j in range(k):
            ln += 1
            tenor = rnd.choice([3, 6, 9, 12])
            principal = rnd.choice([500, 800, 1000, 1500, 2000, 2500, 3000, 4000])
            disb = start + timedelta(days=j * rnd.randint(200, 260))
            last_loan = j == k - 1
            active = last_loan and rnd.random() < 0.72 or (j == k - 2 and rnd.random() < 0.12)
            due = [disb + timedelta(days=30 * i) for i in range(1, tenor + 1)]
            if active and due[-1] <= AS_OF:                      # an "active" loan has to still be running
                disb = AS_OF - timedelta(days=rnd.randint(20, 30 * tenor - 5))
                due = [disb + timedelta(days=30 * i) for i in range(1, tenor + 1)]
            unpaid_from = None
            if active and rnd.random() < 0.22:                   # in arrears: the first overdue installment is unpaid
                overdue = [i for i, d in enumerate(due) if d <= AS_OF]
                if overdue:
                    unpaid_from = overdue[max(0, len(overdue) - rnd.randint(1, min(3, len(overdue))))]
            rows = []
            for i, d in enumerate(due):
                amt = round(principal * (1 + 0.035 * tenor) / tenor, 2)
                if d > AS_OF:
                    paid = None
                elif unpaid_from is not None and i >= unpaid_from:
                    paid = None
                else:
                    paid = d + timedelta(days=rnd.choice([-2, -1, 0, 0, 0, 1, 2, 3]))
                    paid = min(paid, AS_OF)
                rows.append((i + 1, d, paid, amt))
            remaining = sum(1 for _, _, p, _ in rows if p is None)
            status = "ACTIVE" if active else "CLOSED"
            if not active:
                rows = [(i, d, p or d, a) for i, d, p, a in rows]      # a closed loan was paid in full
                remaining = 0
            outstanding = round(principal * (1 + 0.035 * tenor) * remaining / tenor, 2)
            overdue_dates = [d for _, d, p, _ in rows if p is None and d <= AS_OF]
            arrears = (AS_OF - min(overdue_dates)).days if (active and overdue_dates) else 0
            loan = {"loan_id": f"L{ln:05d}", "member_id": m.id, "product": rnd.choice(["INDIVIDUAL", "INDIVIDUAL", "GROUP"]) if principal <= 2500 else "INDIVIDUAL",
                    "principal": principal, "disbursed": disb.isoformat(), "tenor_months": tenor, "status": status,
                    "outstanding_ghs": outstanding, "arrears_days": arrears}
            m.loans.append(loan)
            loans.append(loan)
            for i, d, p, a in rows:
                repayments.append({"loan_id": loan["loan_id"], "installment": i, "due_date": d.isoformat(), "paid_date": p.isoformat() if p else "", "amount_ghs": a})
    return {"members": members, "loans": loans, "repayments": repayments, "as_of": AS_OF.isoformat()}


# ---------- what a member summary should say ----------

def summary(m: Member) -> dict:
    active = [l for l in m.loans if l["status"] == "ACTIVE"]
    paid = [r["paid_date"] for r in WORLD_REPAYMENTS_BY_MEMBER.get(m.id, []) if r["paid_date"]]
    return {"member_id": m.id, "branch": m.branch, "active_loans": len(active),
            "outstanding_ghs": round(sum(l["outstanding_ghs"] for l in active), 2),
            "max_arrears_days": max([l["arrears_days"] for l in active], default=0),
            "last_repayment_date": max(paid) if paid else None}


WORLD_REPAYMENTS_BY_MEMBER: dict[str, list] = {}


def index(world: dict):
    WORLD_REPAYMENTS_BY_MEMBER.clear()
    loan_owner = {l["loan_id"]: l["member_id"] for l in world["loans"]}
    for r in world["repayments"]:
        WORLD_REPAYMENTS_BY_MEMBER.setdefault(loan_owner[r["loan_id"]], []).append(r)
    return world


# ---------- source 1: core banking ----------

def phone_core(national: str) -> str:
    return f"0{national}"


def core_csvs(world: dict) -> dict[str, str]:
    def dump(rows, cols):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
        return buf.getvalue()
    members = [{"member_id": m.id, "full_name": core_name(m), "branch_code": m.branch, "phone": phone_core(m.phone), "village": m.village.upper(), "status": "ACTIVE"}
               for m in world["members"]]
    return {"members": dump(members, ["member_id", "full_name", "branch_code", "phone", "village", "status"]),
            "loans": dump(world["loans"], ["loan_id", "member_id", "product", "principal", "disbursed", "tenor_months", "status", "outstanding_ghs", "arrears_days"]),
            "repayments": dump(world["repayments"], ["loan_id", "installment", "due_date", "paid_date", "amount_ghs"])}


# ---------- source 2: officers' field sheets ----------

def respell(word: str, rnd: random.Random) -> str:
    return rnd.choice(RESPELL[word]) if word in RESPELL and rnd.random() < 0.7 else word


def written_name(m: Member, rnd: random.Random) -> str:
    first, last = respell(m.first, rnd), respell(m.last, rnd)
    style = rnd.choice(["fl", "lf", "fl", "initial", "lf_comma", "first_only_village"])
    if style == "fl":
        return f"{first} {last}"
    if style == "lf":
        return f"{last} {first}"
    if style == "initial":
        return f"{first[0]}. {last}"
    if style == "lf_comma":
        return f"{last}, {first}"
    return f"{first} {last[:3]}."


def field_phone(national: str, rnd: random.Random) -> str:
    r = rnd.random()
    if r < 0.18:
        return ""
    if r < 0.30:
        return f"0{national[:-1]}{rnd.choice('0123456789')}"          # one digit wrong
    return rnd.choice([f"0{national}", f"+233{national}", f"0{national[:2]} {national[2:5]} {national[5:]}", f"{national}"])


OFFICERS = {"TAMALE-C": ["Ruth Alhassan", "Mohammed Iddrisu"], "YENDI": ["Ayishetu Yakubu"], "BOLGA": ["Atinga Ayamga"], "SUNYANI": ["Akua Boateng"]}


def field_sheets(world: dict, seed: int = 99) -> dict[str, tuple[str, list]]:
    """branch -> (csv text, truth). Truth is the member id of each row, in order. It is never written to disk."""
    rnd = random.Random(seed)
    out = {}
    for code in FIELD_SHEET_BRANCHES:
        rows, truth = [], []
        for m in [x for x in world["members"] if x.branch == code]:
            if rnd.random() > 0.55:
                continue
            for _ in range(rnd.choice([1, 1, 1, 2])):               # some members appear twice, spelled differently
                note = rnd.choice(["", "", "repaying well", "asked for top-up", "late again", "new group", "owes small", "travelled"])
                rows.append({"date": (AS_OF - timedelta(days=rnd.randint(1, 40))).isoformat(), "officer": rnd.choice(OFFICERS[code]),
                             "member_name": written_name(m, rnd), "phone": field_phone(m.phone, rnd),
                             "village": rnd.choice([m.village, m.village, m.village, m.village.replace("u", "o")]), "note": note})
                truth.append(m.id)
        order = list(range(len(rows)))
        rnd.shuffle(order)
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["date", "officer", "member_name", "phone", "village", "note"])
        w.writeheader()
        w.writerows([rows[i] for i in order])
        out[code] = (buf.getvalue(), [truth[i] for i in order])
    return out


# ---------- picking members for the acceptance test ----------

def _key(m: Member) -> tuple:
    return (m.branch, m.last[:4].lower(), m.first[0].lower())


def uat_picks(world: dict) -> dict:
    """Deterministic members with interesting, unambiguous properties."""
    ms = world["members"]
    count = {}
    for m in ms:
        count[_key(m)] = count.get(_key(m), 0) + 1
    unique = lambda m: count[_key(m)] == 1
    by = lambda code: [m for m in ms if m.branch == code]
    s = summary
    pick: dict[str, Member] = {}

    def take(name, cands):
        pick[name] = next(m for m in cands if m not in pick.values())

    paid = lambda m: s(m)["last_repayment_date"] is not None
    take("tamale_multi", [m for m in by("TAMALE-C") if s(m)["active_loans"] >= 2 and paid(m)])
    take("tamale_arrears", [m for m in by("TAMALE-C") if s(m)["max_arrears_days"] > 0 and paid(m)])
    take("tamale_clean", [m for m in by("TAMALE-C") if s(m)["active_loans"] == 1 and s(m)["max_arrears_days"] == 0 and paid(m)])
    take("tamale_none", [m for m in by("TAMALE-C") if s(m)["active_loans"] == 0 and paid(m)])
    take("tamale_name1", [m for m in by("TAMALE-C") if unique(m) and s(m)["active_loans"] >= 1 and paid(m)][3:])
    take("tamale_name2", [m for m in by("TAMALE-C") if unique(m) and m.last in RESPELL and paid(m)])
    take("tamale_name3", [m for m in by("TAMALE-C") if unique(m) and m.first in RESPELL and m.last not in RESPELL and paid(m)])
    take("yendi_phone", [m for m in by("YENDI") if s(m)["active_loans"] >= 1 and paid(m)][2:])
    take("bolga_target", [m for m in by("BOLGA") if s(m)["active_loans"] >= 1 and s(m)["outstanding_ghs"] > 100 and paid(m)][1:])
    take("sunyani_phone", [m for m in by("SUNYANI") if s(m)["active_loans"] >= 1 and paid(m)][1:])
    return pick
