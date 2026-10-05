"""Generate three messy, overlapping customer exports for the reconciliation lab.

Usage:
    python make_messy_data.py                  # fresh dataset, seed 1
    python make_messy_data.py --seed 2 --append  # add new rows (incremental-load stretch goal)

Writes data/crm.csv, data/billing.json, data/ops_sheet.csv and the hidden
ground truth in .truth/ (don't read it - check.py scores you against it).
"""

import argparse
import csv
import json
import random
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
TRUTH = HERE / ".truth"

FIRST = ["Kwame", "Kofi", "Kwabena", "Yaw", "Kwaku", "Kojo", "Kwesi", "Ama", "Akosua",
         "Abena", "Adwoa", "Yaa", "Afua", "Esi", "Efua", "Ekow", "Nana", "Selorm",
         "Elikem", "Dzifa", "Mawuli", "Fatima", "Ibrahim", "Abdul", "Grace", "Emmanuel",
         "Comfort", "Samuel", "Gifty", "Daniel", "Patience", "Isaac", "Mercy", "Joseph"]
LAST = ["Mensah", "Owusu", "Boateng", "Asante", "Osei", "Agyeman", "Appiah", "Darko",
        "Addo", "Quaye", "Tetteh", "Ofori", "Amoah", "Danso", "Nkrumah", "Agboada",
        "Kumi", "Sarpong", "Frimpong", "Badu", "Adjei", "Annan", "Mahama", "Yeboah"]
TOWNS = ["Kumasi", "Accra", "Tema", "Takoradi", "Cape Coast", "Tamale", "Ho", "Koforidua",
         "Sunyani", "Obuasi", "Techiman", "Kasoa"]
LANDMARKS = ["near the Total station", "opp. the church", "behind the market",
             "by the big mango tree", "next to the school", "junction, blue gate"]
BIZ_SUFFIX = ["Enterprise", "Ventures", "Provisions", "& Sons", "Trading", "Chop Bar", "Mini Mart"]
PREFIXES = ["024", "054", "055", "059", "020", "050", "027", "026", "057"]
TITLES = ["Mr.", "Mrs.", "Ms.", "Dr.", "Madam", "Alhaji", "Rev."]


def new_customer(rng: random.Random, cid: int) -> dict:
    first, last = rng.choice(FIRST), rng.choice(LAST)
    phone = rng.choice(PREFIXES) + "".join(rng.choice("0123456789") for _ in range(7))
    alt_phone = rng.choice(PREFIXES) + "".join(rng.choice("0123456789") for _ in range(7))
    domain = rng.choice(["gmail.com", "yahoo.com", "outlook.com"])
    sep = rng.choice([".", "", "_"])
    email = f"{first.lower()}{sep}{last.lower()}{rng.randint(1, 99) if rng.random() < 0.5 else ''}@{domain}"
    return {
        "cid": f"C{cid:04d}",
        "first": first,
        "last": last,
        "phone": phone,
        "alt_phone": alt_phone,
        "email": email,
        "town": rng.choice(TOWNS),
        "business": f"{rng.choice([first, last, first + ' ' + last])} {rng.choice(BIZ_SUFFIX)}",
    }


# ---------- mess functions ----------

def mess_phone(rng: random.Random, p: str) -> str:
    local = p[1:]  # drop leading 0
    return rng.choice([
        p,
        f"+233 {local[:2]} {local[2:5]} {local[5:]}",
        f"233{local}",
        f"{p[:3]}-{p[3:6]}-{p[6:]}",
        f"({p[:3]}) {p[3:]}",
        f"+233{local}",
        f"{p[:3]} {p[3:]}",
    ])


def typo(rng: random.Random, s: str) -> str:
    if len(s) < 4:
        return s
    i = rng.randrange(1, len(s) - 1)
    op = rng.choice(["drop", "swap", "double"])
    if op == "drop":
        return s[:i] + s[i + 1:]
    if op == "swap":
        return s[:i] + s[i + 1] + s[i] + s[i + 2:]
    return s[:i] + s[i] + s[i:]


def mess_name(rng: random.Random, first: str, last: str) -> str:
    if rng.random() < 0.15:
        first = typo(rng, first)
    if rng.random() < 0.1:
        last = typo(rng, last)
    form = rng.choice(["fl", "fl", "fl", "lf_comma", "upper", "title", "initial"])
    if form == "lf_comma":
        return f"{last}, {first}"
    if form == "upper":
        return f"{first} {last}".upper()
    if form == "title":
        return f"{rng.choice(TITLES)} {first} {last}"
    if form == "initial":
        return f"{first[0]}. {last}"
    return f"{first} {last}"


def mess_email(rng: random.Random, e: str) -> str:
    r = rng.random()
    if r < 0.2:
        return e.upper()
    if r < 0.3:
        return f"  {e} "
    if r < 0.4:
        return ""
    return e


# ---------- record emitters ----------

def crm_rows(rng, c, start_id):
    rows = [{
        "crm_id": start_id,
        "full_name": mess_name(rng, c["first"], c["last"]),
        "email": mess_email(rng, c["email"]),
        "phone": mess_phone(rng, c["phone"]),
        "city": c["town"] if rng.random() > 0.1 else c["town"].upper(),
        "created_at": f"20{rng.randint(19, 25)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
    }]
    if rng.random() < 0.12:  # in-system duplicate (sales rep re-entered them)
        dup = dict(rows[0])
        dup["crm_id"] = start_id + 1
        dup["full_name"] = mess_name(rng, c["first"], c["last"])
        dup["phone"] = mess_phone(rng, c["phone"]) if rng.random() < 0.7 else mess_phone(rng, c["alt_phone"])
        dup["email"] = mess_email(rng, c["email"])
        rows.append(dup)
    return rows


def billing_row(rng, c, acct_no):
    momo = c["phone"] if rng.random() < 0.75 else c["alt_phone"]
    holder = c["business"] if rng.random() < 0.5 else mess_name(rng, c["first"], c["last"])
    return {
        "account_no": f"A-{acct_no:04d}",
        "account_name": holder,
        "contact": {"momo_number": mess_phone(rng, momo), "email": mess_email(rng, c["email"]) or None},
        "region_town": c["town"],
        "balance_ghs": round(rng.uniform(-500, 4000), 2),
    }


def ops_row(rng, c, row_no):
    nick = rng.choice([c["first"], f"{c['first']} {c['last'][0]}.", f"{c['first']} ({c['business']})",
                       c["business"], f"{c['last']} - {c['town']}"])
    if rng.random() < 0.2:
        nick = typo(rng, nick)
    phone = c["phone"] if rng.random() < 0.85 else c["alt_phone"]
    return {
        "row": row_no,
        "Customer": nick,
        "Tel": mess_phone(rng, phone) if rng.random() > 0.08 else "",
        "Location": f"{c['town']}, {rng.choice(LANDMARKS)}",
        "Notes": rng.choice(["", "", "pays late", "prefers morning drop", "call before coming", "VIP"]),
    }


def junk_rows(rng, n, crm_start, ops_start):
    crm, ops = [], []
    for i in range(n):
        crm.append({"crm_id": crm_start + i, "full_name": rng.choice(["TEST", "test user", "asdf", "Walk-in"]),
                    "email": "", "phone": rng.choice(["0000000000", "", "0244000000"]), "city": "",
                    "created_at": "2024-01-01"})
        ops.append({"row": ops_start + i, "Customer": rng.choice(["??", "cash customer", "x"]),
                    "Tel": "", "Location": "", "Notes": "ignore"})
    return crm, ops


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--customers", type=int, default=150)
    ap.add_argument("--append", action="store_true", help="add rows to an existing dataset")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    DATA.mkdir(exist_ok=True)
    TRUTH.mkdir(exist_ok=True)

    if args.append:
        state = json.loads((TRUTH / "state.json").read_text())
        customers = state["customers"]
        clusters = {c["customer_id"]: c["members"] for c in json.loads((TRUTH / "clusters.json").read_text())}
        crm = list(csv.DictReader((DATA / "crm.csv").open(encoding="utf-8")))
        billing = json.loads((DATA / "billing.json").read_text(encoding="utf-8"))
        ops = list(csv.DictReader((DATA / "ops_sheet.csv").open(encoding="utf-8")))
        nxt = state["next"]
        # some existing customers show up again, plus some brand-new ones
        touched = rng.sample(customers, k=min(20, len(customers)))
        for i in range(args.customers // 5):
            touched.append(new_customer(rng, len(customers) + i + 1))
        customers += [c for c in touched if c["cid"] not in clusters]
    else:
        customers = [new_customer(rng, i + 1) for i in range(args.customers)]
        clusters, crm, billing, ops = {}, [], [], []
        nxt = {"crm": 1001, "billing": 1, "ops": 2}
        touched = customers

    for c in touched:
        members = clusters.setdefault(c["cid"], [])
        if rng.random() < 0.9:
            rows = crm_rows(rng, c, nxt["crm"])
            nxt["crm"] += len(rows)
            crm += rows
            members += [f"crm:{r['crm_id']}" for r in rows]
        if rng.random() < 0.8 and not any(m.startswith("billing:") for m in members):
            b = billing_row(rng, c, nxt["billing"])
            nxt["billing"] += 1
            billing.append(b)
            members.append(f"billing:{b['account_no']}")
        if rng.random() < 0.7:
            o = ops_row(rng, c, nxt["ops"])
            nxt["ops"] += 1
            ops.append(o)
            members.append(f"ops:{o['row']}")
        if not members:
            del clusters[c["cid"]]

    if not args.append:
        jc, jo = junk_rows(rng, 6, nxt["crm"], nxt["ops"])
        nxt["crm"] += len(jc)
        nxt["ops"] += len(jo)
        crm += jc
        ops += jo
        for r in jc:
            clusters[f"JUNK-crm-{r['crm_id']}"] = [f"crm:{r['crm_id']}"]
        for r in jo:
            clusters[f"JUNK-ops-{r['row']}"] = [f"ops:{r['row']}"]

    rng.shuffle(crm)
    rng.shuffle(ops)

    with (DATA / "crm.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["crm_id", "full_name", "email", "phone", "city", "created_at"])
        w.writeheader()
        w.writerows(crm)
    (DATA / "billing.json").write_text(json.dumps(billing, indent=2), encoding="utf-8")
    with (DATA / "ops_sheet.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["row", "Customer", "Tel", "Location", "Notes"])
        w.writeheader()
        w.writerows(ops)

    (TRUTH / "clusters.json").write_text(
        json.dumps([{"customer_id": k, "members": v} for k, v in clusters.items()], indent=2))
    (TRUTH / "state.json").write_text(json.dumps({"customers": customers, "next": nxt}))

    print(f"crm: {len(crm)} rows | billing: {len(billing)} accounts | ops: {len(ops)} rows | "
          f"true customers (incl. junk singletons): {len(clusters)}")


if __name__ == "__main__":
    main()
