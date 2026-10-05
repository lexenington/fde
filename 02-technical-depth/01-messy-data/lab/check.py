"""Score your clusters against the hidden truth with pairwise precision / recall / F1.

Usage: python check.py out/clusters.json
"""

import json
import sys
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).parent


def pairs(clusters):
    out = set()
    for c in clusters:
        for a, b in combinations(sorted(set(c["members"])), 2):
            out.add((a, b))
    return out


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    truth = json.loads((HERE / ".truth" / "clusters.json").read_text())
    pred = json.loads(Path(sys.argv[1]).read_text())

    all_ids = {m for c in truth for m in c["members"]}
    pred_ids = [m for c in pred for m in c["members"]]
    unknown = set(pred_ids) - all_ids
    missing = all_ids - set(pred_ids)
    dupes = {m for m in pred_ids if pred_ids.count(m) > 1}

    tp_pairs, pred_pairs = pairs(truth), pairs(pred)
    tp = len(tp_pairs & pred_pairs)
    precision = tp / len(pred_pairs) if pred_pairs else 0.0
    recall = tp / len(tp_pairs) if tp_pairs else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    print(f"records in truth:      {len(all_ids)}")
    print(f"clusters truth / yours: {len(truth)} / {len(pred)}")
    print(f"unassigned records:    {len(missing)}   (treated as singletons)")
    if unknown:
        print(f"UNKNOWN ids in yours:  {len(unknown)}  e.g. {sorted(unknown)[:5]}")
    if dupes:
        print(f"ids in >1 cluster:     {len(dupes)}  e.g. {sorted(dupes)[:5]}  <- every record must be in exactly one")
    print()
    print(f"pairwise precision: {precision:.3f}   (of pairs you merged, how many are truly the same customer)")
    print(f"pairwise recall:    {recall:.3f}   (of true same-customer pairs, how many you found)")
    print(f"F1:                 {f1:.3f}   target >= 0.92")

    false_merges = sorted(pred_pairs - tp_pairs)[:5]
    missed = sorted(tp_pairs - pred_pairs)[:5]
    if false_merges:
        print("\nsample false merges:", false_merges)
    if missed:
        print("sample missed merges:", missed)


if __name__ == "__main__":
    main()
