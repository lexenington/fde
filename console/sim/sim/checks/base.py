"""Tiny check framework: each check passes with a detail string, or raises Fail/Blocked."""

import json
import time
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

    def run(self, ctx) -> dict:
        results = []
        for c in self.checks:
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
            results.append(Result(c.id, c.section, c.title, c.points, status, detail, c.hint,
                                  round(time.perf_counter() - t0, 2)))
            if c.id == "preflight" and status != "pass":
                for rest in self.checks[1:]:
                    results.append(Result(rest.id, rest.section, rest.title, rest.points, "blocked",
                                          "app not reachable", rest.hint, 0))
                break
        score = sum(r.points for r in results if r.status == "pass")
        total = sum(c.points for c in self.checks)
        return {
            "lab": self.lab, "title": self.title, "run_id": ctx.run_id,
            "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "learner_url": ctx.learner_url, "score": score, "total": total,
            "passed": sum(r.status == "pass" for r in results), "count": len(results),
            "results": [asdict(r) for r in results],
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
