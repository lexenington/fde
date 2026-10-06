"""Tiny check framework: each check passes with a detail string, or raises Fail/Blocked."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httpx


class Fail(Exception):
    pass


class Blocked(Exception):
    pass


@dataclass
class Check:
    id: str
    section: str
    title: str
    points: int
    hint: str
    fn: Callable
    tags: list = field(default_factory=list)
    serial: bool = False        # must not run alongside other checks (it changes shared state)


@dataclass
class Result:
    id: str
    section: str
    title: str
    points: int
    status: str  # pass | fail | blocked | error
    detail: str
    hint: str
    seconds: float
    tags: list = field(default_factory=list)


@dataclass
class Suite:
    lab: str
    title: str
    checks: list[Check] = field(default_factory=list)

    def check(self, id: str, section: str, title: str, points: int, hint: str):
        def deco(fn):
            self.checks.append(Check(id, section, title, points, hint, fn))
            return fn
        return deco

    def _one(self, ctx, c: Check) -> Result:
        t0 = time.perf_counter()
        try:
            status, detail = "pass", c.fn(ctx) or "ok"
        except Fail as e:
            status, detail = "fail", str(e)
        except Blocked as e:
            status, detail = "blocked", str(e)
        except httpx.ConnectError:
            status, detail = "fail", f"could not connect to your app at {ctx.learner_url}"
        except httpx.TimeoutException:
            status, detail = "fail", "your app did not answer within the timeout"
        except Exception as e:  # a bug in a check should not kill the run
            status, detail = "error", f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=2)}"
        ctx.status[c.id] = status
        return Result(c.id, c.section, c.title, c.points, status, detail, c.hint, round(time.perf_counter() - t0, 2), c.tags)

    def run(self, ctx, workers: int = 1, only: set[str] | None = None, progress: Callable | None = None) -> dict:
        """Run the checks. `workers` > 1 runs independent checks in parallel (after the preflight check).
        `only` limits the run to those sections or check ids. `progress(done, total, title)` is called as checks finish."""
        todo = [c for c in self.checks if not only or c.section in only or c.id in only or c.id == "preflight"]
        results: dict[str, Result] = {}
        done = 0

        def finish(r: Result):
            nonlocal done
            results[r.id] = r
            done += 1
            if progress:
                progress(done, len(todo), r.title)

        first = todo[0] if todo and todo[0].id == "preflight" else None
        rest = todo[1:] if first else todo
        if first:
            finish(self._one(ctx, first))
        if first and results["preflight"].status != "pass":
            for c in rest:
                finish(Result(c.id, c.section, c.title, c.points, "blocked", "app not reachable", c.hint, 0, c.tags))
        else:
            parallel = [c for c in rest if not c.serial] if workers > 1 else []
            serial = [c for c in rest if c not in parallel]
            if parallel:
                with ThreadPoolExecutor(workers) as pool:
                    for r in pool.map(lambda c: self._one(ctx, c), parallel):
                        finish(r)
            for c in serial:
                finish(self._one(ctx, c))
        ordered = [results[c.id] for c in todo]
        score = sum(r.points for r in ordered if r.status == "pass")
        return {
            "lab": self.lab, "title": self.title, "run_id": ctx.run_id,
            "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "learner_url": ctx.learner_url, "score": score, "total": sum(c.points for c in todo),
            "passed": sum(r.status == "pass" for r in ordered), "count": len(ordered),
            "results": [asdict(r) for r in ordered],
        }


def save_run(runs_dir: Path, run: dict) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{run['run_id']}.json"
    path.write_text(json.dumps(run, indent=2), encoding="utf-8")
    return path


def list_runs(runs_dir: Path) -> list[dict]:
    if not runs_dir.exists():
        return []
    out = []
    for p in sorted(runs_dir.glob("*.json")):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        out.append({k: r.get(k) for k in ("run_id", "finished_at", "score", "total", "passed", "count")})
    return out


def expect(resp: httpx.Response, allowed: set[int] | range, what: str):
    if resp.status_code not in allowed:
        body = resp.text[:300].replace("\n", " ")
        raise Fail(f"{what}: expected {sorted(allowed) if isinstance(allowed, set) else 'a 2xx'}, got {resp.status_code} {body}")
    return resp
