"""Lab 02/01 scorer: the same pairwise F1 as check.py, plus what check.py can't show well: the raw rows behind
each wrong merge and each missed merge, and a log of the score over time with a note on what you changed.

Reads the learner's `out/clusters.json` and the lab's hidden truth. The truth never leaves this module: only the
learner's own mistakes are returned, as the source rows you already have in data/.
"""

import csv
import json
from datetime import datetime, timezone
from itertools import combinations

from . import config

LAB = "01-messy-data"
TARGET_F1 = 0.92


def lab_dir():
    return config.LABS_DIR / LAB / "lab"


def runs_dir():
    return lab_dir() / "runs"


def _pairs(clusters):
    return {p for c in clusters for p in combinations(sorted(set(c["members"])), 2)}


def _rows():
    """record id ('crm:1001', 'billing:7', 'ops:3') -> the raw row, as the learner's data/ files have it."""
    d, out = lab_dir() / "data", {}
    if (d / "crm.csv").exists():
        for r in csv.DictReader((d / "crm.csv").open(encoding="utf-8")):
            out[f"crm:{r['crm_id']}"] = r
    if (d / "billing.json").exists():
        for r in json.loads((d / "billing.json").read_text(encoding="utf-8")):
            out[f"billing:{r['account_no']}"] = r
    if (d / "ops_sheet.csv").exists():
        for r in csv.DictReader((d / "ops_sheet.csv").open(encoding="utf-8")):
            out[f"ops:{r['row']}"] = r
    return out


class NotReady(Exception):
    pass


def status():
    truth = lab_dir() / ".truth" / "clusters.json"
    return {"data_ready": truth.exists() and (lab_dir() / "data" / "crm.csv").exists(),
            "clusters_path": "02-technical-depth/01-messy-data/lab/out/clusters.json",
            "clusters_found": (lab_dir() / "out" / "clusters.json").exists(), "target_f1": TARGET_F1}


def score(note: str = "", examples: int = 6):
    truth_p, pred_p = lab_dir() / ".truth" / "clusters.json", lab_dir() / "out" / "clusters.json"
    if not truth_p.exists():
        raise NotReady("No data yet. In the lab folder run: python make_messy_data.py")
    if not pred_p.exists():
        raise NotReady("No out/clusters.json yet. Write your clusters as [{\"members\": [\"crm:1001\", \"billing:3\", ...]}, ...]")
    truth = json.loads(truth_p.read_text(encoding="utf-8"))
    try:
        pred = json.loads(pred_p.read_text(encoding="utf-8"))
        pred_ids = [m for c in pred for m in c["members"]]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise NotReady(f"out/clusters.json isn't in the expected shape ({type(e).__name__}). Expected a list of {{\"members\": [...]}}.")

    all_ids = {m for c in truth for m in c["members"]}
    unknown, missing = set(pred_ids) - all_ids, all_ids - set(pred_ids)
    dupes = sorted({m for m in pred_ids if pred_ids.count(m) > 1})
    t_pairs, p_pairs = _pairs(truth), _pairs(pred)
    tp = len(t_pairs & p_pairs)
    precision = tp / len(p_pairs) if p_pairs else 0.0
    recall = tp / len(t_pairs) if t_pairs else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    # Show errors where it teaches: a false merge is explained by the two rows that look alike
    rows = _rows()
    show = lambda ids: [{"id": i, "row": rows.get(i)} for i in ids]
    fm, ms = sorted(p_pairs - t_pairs), sorted(t_pairs - p_pairs)
    junk = {m for c in truth if str(c.get("customer_id", "")).startswith("JUNK") for m in c["members"]}
    result = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": note.strip()[:400],
        "records": len(all_ids), "clusters_truth": len(truth), "clusters_yours": len(pred),
        "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
        "target_f1": TARGET_F1, "passed": f1 >= TARGET_F1,
        "false_merge_pairs": len(fm), "missed_pairs": len(ms),
        "unassigned": len(missing), "unknown_ids": sorted(unknown)[:5], "unknown_count": len(unknown),
        "in_multiple_clusters": dupes[:5], "multi_count": len(dupes),
        "junk_merged": sorted({m for p in fm for m in p if m in junk})[:5],
    }
    saved = dict(result)
    runs_dir().mkdir(parents=True, exist_ok=True)
    (runs_dir() / f"{result['run_id']}.json").write_text(json.dumps(saved, indent=2), encoding="utf-8")
    result["false_merges"] = [{"pair": show(p)} for p in fm[:examples]]
    result["missed"] = [{"pair": show(p)} for p in ms[:examples]]
    return result


def history():
    if not runs_dir().exists():
        return []
    out = []
    for p in sorted(runs_dir().glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out
