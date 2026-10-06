"""Katas: 30-60 minute drills whose tests are already written. The Console just runs the learner's pytest and shows the result."""

import re
import subprocess
import sys

from . import config


def _meta(d):
    readme = (d / "README.md").read_text(encoding="utf-8") if (d / "README.md").exists() else ""
    title = re.search(r"^#\s*(.+)$", readme, re.M)
    box = re.search(r"Time-box:\s*([^*]+)\*\*", readme)
    used = re.search(r"Used in:\s*(.+)", readme)
    return {"id": d.name, "title": title.group(1).strip() if title else d.name,
            "timebox": box.group(1).strip() if box else "", "used_in": used.group(1).strip() if used else "",
            "readme": readme}


def _dirs():
    return sorted(p for p in config.KATAS_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")) if config.KATAS_DIR.exists() else []


def list_katas():
    return [{k: v for k, v in _meta(d).items() if k != "readme"} for d in _dirs()]


def detail(kata_id):
    d = config.KATAS_DIR / kata_id
    if not d.is_dir() or d.parent != config.KATAS_DIR:
        return None
    return _meta(d)


def _trim(out, head=3000):
    """The first failures are the useful part (the learner reads one at a time); keep the summary line too."""
    lines = out.rstrip().splitlines()
    return out if len(out) <= head else out[:head].rstrip() + "\n...\n" + (lines[-1] if lines else "")


def run(kata_id, timeout=60):
    """Run the learner's tests for one kata. Returns counts and the output of the first failures."""
    d = config.KATAS_DIR / kata_id
    if not d.is_dir() or d.parent != config.KATAS_DIR:
        return None
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--tb=short", str(d)],
                           capture_output=True, text=True, timeout=timeout, cwd=str(d))
    except subprocess.TimeoutExpired:
        return {"id": kata_id, "passed": 0, "failed": 0, "output": f"Timed out after {timeout}s. An infinite loop, or a sleep that should use the injected clock?", "timed_out": True}
    out = r.stdout + r.stderr
    n = lambda w: int(m.group(1)) if (m := re.search(rf"(\d+) {w}", out)) else 0
    return {"id": kata_id, "passed": n("passed"), "failed": n("failed") + n("error"), "output": _trim(out), "timed_out": False}
