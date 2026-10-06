def routing_table(results, thresholds):
    rows, total = [], len(results)
    for t in thresholds:
        auto = [r for r in results if r["confidence"] >= t]
        wrong = sum(1 for r in auto if not r["correct"])
        rows.append({"threshold": t, "auto": len(auto), "review": total - len(auto),
                     "auto_pct": round(100 * len(auto) / total, 1) if total else 0.0,
                     "error_pct": round(100 * wrong / len(auto), 1) if auto else 0.0,
                     "leaked": sum(1 for r in auto if r["must_review"])})
    return rows


def pick_threshold(table, *, max_error_pct, max_leaked=0):
    ok = [r["threshold"] for r in table if r["error_pct"] <= max_error_pct and r["leaked"] <= max_leaked]
    return min(ok) if ok else None
