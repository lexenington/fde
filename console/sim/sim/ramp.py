"""Lab 02/05: a timeboxed ramp. A clock, six milestones stamped as you reach them, and a check of what you wrote.

The ramp log is the point: where the hours went. Stamping milestones as you go gives you the real timeline instead of
a reconstruction from memory, and a second ramp two weeks later can be set beside the first.
"""

import json
import re
import time
from datetime import datetime, timezone

from . import config

LAB = "05-unfamiliar-territory"
DAY_HOURS = 8
MILESTONES = [
    ("running", "Running locally with seed data"),
    ("trace", "Traced one real request end to end"),
    ("architecture", "ARCHITECTURE.md written"),
    ("datamap", "GLOSSARY.md and DATA-MAP.md written"),
    ("change", "One small change behind a flag, with a test"),
    ("log", "RAMP-LOG.md written"),
]
KEYS = [k for k, _ in MILESTONES]


def lab_dir():
    return config.LABS_DIR / LAB / "lab"


def _path():
    return lab_dir() / "ramps.json"


def _load():
    p = _path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"ramps": []}


def _save(d):
    _path().parent.mkdir(parents=True, exist_ok=True)
    _path().write_text(json.dumps(d, indent=2), encoding="utf-8")


def _active(d):
    return next((r for r in d["ramps"] if r.get("ended") is None), None)


def start(codebase, now=None):
    codebase = codebase.strip()
    if not codebase:
        raise ValueError("Say which codebase you're ramping on (Odoo, ERPNext, Saleor…).")
    d = _load()
    if _active(d):
        raise ValueError("A ramp is already running. Finish or abandon it first.")
    d["ramps"].append({"n": len(d["ramps"]) + 1, "codebase": codebase[:80], "started": now if now is not None else time.time(), "ended": None, "marks": {}})
    _save(d)
    return state(now)


def mark(key, note="", now=None):
    if key not in KEYS:
        raise ValueError("unknown milestone")
    d = _load()
    r = _active(d)
    if not r:
        raise ValueError("No ramp is running.")
    t = now if now is not None else time.time()
    r["marks"][key] = {"at": t, "minutes": round((t - r["started"]) / 60, 1), "note": note.strip()[:300]}
    _save(d)
    return state(now)


def unmark(key):
    d = _load()
    r = _active(d)
    if r:
        r["marks"].pop(key, None)
        _save(d)
    return state()


def finish(abandon=False, now=None):
    d = _load()
    r = _active(d)
    if not r:
        raise ValueError("No ramp is running.")
    r["ended"] = now if now is not None else time.time()
    r["abandoned"] = abandon
    _save(d)
    return state(now)


def skeleton(r):
    """The RAMP-LOG.md timeline, from your own stamps. You add the 'why' and the 'faster next time'."""
    rows = sorted(r["marks"].items(), key=lambda kv: kv[1]["at"])
    prev, lines = 0.0, [f"# Ramp log: {r['codebase']} (ramp #{r['n']})", "", "| Elapsed | Milestone | Took | What happened |", "|---|---|---|---|"]
    labels = dict(MILESTONES)
    for k, m in rows:
        lines.append(f"| {m['minutes']:g} min | {labels[k]} | {m['minutes'] - prev:g} min | {m['note'] or ''} |")
        prev = m["minutes"]
    lines += ["", "## Where I lost time", "", "## What I'll do faster next time", ""]
    return "\n".join(lines)


def _docs():
    d, out = lab_dir(), []

    def read(n):
        p = d / n
        return p.read_text(encoding="utf-8") if p.exists() else None

    arch = read("ARCHITECTURE.md")
    if arch is None:
        out.append({"doc": "ARCHITECTURE.md", "exists": False, "checks": []})
    else:
        w = len(arch.split())
        heads = " ".join(l for l in arch.splitlines() if l.startswith("#")).lower()
        out.append({"doc": "ARCHITECTURE.md", "exists": True, "words": w, "checks": [
            {"label": "one page (under 600 words)", "ok": w <= 600},
            {"label": "components", "ok": bool(re.search(r"component|service|module|architecture", heads))},
            {"label": "a request flow", "ok": bool(re.search(r"flow|request|journey|trace", heads))},
            {"label": "where the data lives", "ok": bool(re.search(r"data|database|storage|store", heads))}]})
    gl = read("GLOSSARY.md")
    terms = len([l for l in (gl or "").splitlines() if re.match(r"\s*([-*|]|\*\*|#{2,3} )", l) and len(l.strip()) > 8])
    out.append({"doc": "GLOSSARY.md", "exists": gl is not None, "checks": [] if gl is None else [{"label": f"{terms} terms (aim for 15+)", "ok": terms >= 15}]})
    dm = read("DATA-MAP.md")
    tables = len(set(re.findall(r"`([a-z_][a-z0-9_.]{2,})`", dm or "", re.I)))
    out.append({"doc": "DATA-MAP.md", "exists": dm is not None, "checks": [] if dm is None else [{"label": f"{tables} tables named in `code` (the brief says 10)", "ok": tables >= 10}]})
    rl = read("RAMP-LOG.md")
    out.append({"doc": "RAMP-LOG.md", "exists": rl is not None, "checks": [] if rl is None else [
        {"label": "says where you lost time", "ok": bool(re.search(r"lost|slow|stuck|wasted", rl, re.I))},
        {"label": "says what you'll do faster", "ok": bool(re.search(r"faster|next time|differently", rl, re.I))}]})
    return out


def state(now=None):
    d = _load()
    t = now if now is not None else time.time()
    a = _active(d)
    ramps = []
    for r in d["ramps"]:
        end = r["ended"] or t
        ramps.append({**r, "elapsed_min": round((end - r["started"]) / 60, 1), "over_day": (end - r["started"]) > DAY_HOURS * 3600})
    done = [r for r in ramps if r["ended"] is not None and not r.get("abandoned")]
    compare = None
    if len(done) >= 2:
        a1, b1 = done[0], done[-1]
        compare = {"first": a1["n"], "latest": b1["n"], "rows": [
            {"milestone": lbl, "first": a1["marks"].get(k, {}).get("minutes"), "latest": b1["marks"].get(k, {}).get("minutes")} for k, lbl in MILESTONES]}
    return {"day_hours": DAY_HOURS, "milestones": [{"key": k, "label": l} for k, l in MILESTONES], "active": a["n"] if a else None, "ramps": ramps,
            "docs": _docs(), "skeleton": skeleton(a) if a else (skeleton(done[-1]) if done else None), "compare": compare,
            "lab_path": "02-technical-depth/05-unfamiliar-territory/lab"}
