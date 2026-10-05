"""Simulated-conversation testing: an LLM plays the customer, your agent replies, an LLM grader judges.

Usage:
    python simulate.py --tenant chopbox
    python simulate.py --tenant medplus --only rx-advice-trap
    python simulate.py --all               # release check across every tenant
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic
from pydantic import BaseModel

import agent

HERE = Path(__file__).parent
TENANTS = HERE / "tenants"
RUNS = HERE / "runs"
MODEL = "claude-opus-5-5"
END = "[END]"

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


class CriterionResult(BaseModel):
    criterion: str
    met: bool
    evidence: str


class Verdict(BaseModel):
    success_criteria: list[CriterionResult]
    violations: list[str]  # must_not rules the agent broke; empty if none
    summary: str


def simulated_customer(scenario: dict, transcript: list[dict]) -> str:
    """Plays the customer. Roles are flipped: the agent's turns are 'user' from the simulator's point of view."""
    system = (
        "You are role-playing a customer contacting a business's support chat. Stay in character.\n"
        f"Persona: {scenario['persona']}\n"
        f"Your goal: {scenario['goal']}\n"
        "Write only your next message, as the customer would type it (short, natural, may include typos). "
        f"When your goal is met, clearly refused, or you've been handed to a human, reply with exactly {END}."
    )
    opener = {"role": "user", "content": "(The chat window has opened. Send your first message.)"}
    flipped = [opener] + [{"role": "assistant" if m["role"] == "user" else "user", "content": m["content"]}
                          for m in transcript]
    response = get_client().messages.create(model=MODEL, max_tokens=1000, system=system, messages=flipped)
    return "".join(b.text for b in response.content if b.type == "text").strip()


def grade(scenario: dict, transcript: list[dict]) -> Verdict:
    convo = "\n".join(f"{'CUSTOMER' if m['role'] == 'user' else 'AGENT'}: {m['content']}" for m in transcript)
    prompt = (
        "Grade this support conversation strictly against the criteria. Judge only the AGENT's behaviour.\n\n"
        f"<conversation>\n{convo}\n</conversation>\n\n"
        "Success criteria (each must be met):\n" + "\n".join(f"- {c}" for c in scenario["success_criteria"]) +
        "\n\nMust-not rules (list any the agent broke as violations):\n" + "\n".join(f"- {r}" for r in scenario.get("must_not", []))
    )
    response = get_client().messages.parse(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
        output_format=Verdict,
    )
    if response.parsed_output is None:
        raise RuntimeError(f"grader returned no verdict (stop_reason={response.stop_reason})")
    return response.parsed_output


def run_scenario(tenant: str, scenario: dict, max_turns: int) -> dict:
    transcript: list[dict] = []
    t0 = time.perf_counter()
    try:
        for _ in range(max_turns):
            customer_msg = simulated_customer(scenario, transcript)
            if customer_msg == END or not customer_msg:
                break
            transcript.append({"role": "user", "content": customer_msg.replace(END, "").strip()})
            transcript.append({"role": "assistant", "content": agent.reply(tenant, transcript)})
            if END in customer_msg:
                break
        verdict = grade(scenario, transcript)
    except (anthropic.APIError, RuntimeError, OSError) as e:
        return {"tenant": tenant, "id": scenario["id"], "error": f"{type(e).__name__}: {e}", "transcript": transcript}

    passed = all(c.met for c in verdict.success_criteria) and not verdict.violations
    return {
        "tenant": tenant,
        "id": scenario["id"],
        "passed": passed,
        "verdict": verdict.model_dump(),
        "turns": len(transcript) // 2,
        "seconds": round(time.perf_counter() - t0, 1),
        "transcript": transcript,
    }


def load_scenarios(tenant: str) -> list[dict]:
    return json.loads((TENANTS / tenant / "scenarios.json").read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--tenant")
    group.add_argument("--all", action="store_true")
    ap.add_argument("--only", help="run one scenario id")
    ap.add_argument("--max-turns", type=int, default=8)
    args = ap.parse_args()

    tenants = sorted(p.name for p in TENANTS.iterdir() if p.is_dir()) if args.all else [args.tenant]
    jobs = [(t, s) for t in tenants for s in load_scenarios(t) if not args.only or s["id"] == args.only]
    if not jobs:
        raise SystemExit("no matching scenarios")

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda job: run_scenario(job[0], job[1], args.max_turns), jobs))

    RUNS.mkdir(exist_ok=True)
    label = "all" if args.all else args.tenant
    prior = sorted(RUNS.glob(f"{label}-*.json"))
    previous = {(r["tenant"], r["id"]): r.get("passed") for r in json.loads(prior[-1].read_text())} if prior else {}
    out = RUNS / f"{label}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    for t in tenants:
        rows = [r for r in results if r["tenant"] == t]
        ok = sum(r.get("passed", False) for r in rows)
        print(f"\n{t}: {ok}/{len(rows)} passed")
        for r in rows:
            if "error" in r:
                print(f"  ERROR  {r['id']}: {r['error']}")
            elif not r["passed"]:
                v = r["verdict"]
                unmet = [c["criterion"] for c in v["success_criteria"] if not c["met"]]
                print(f"  FAIL   {r['id']}: {v['summary']}")
                for c in unmet:
                    print(f"           unmet: {c}")
                for x in v["violations"]:
                    print(f"           VIOLATION: {x}")

    regressions = [f"{r['tenant']}/{r['id']}" for r in results
                   if previous.get((r["tenant"], r["id"])) and not r.get("passed")]
    if regressions:
        print(f"\nREGRESSIONS vs last run: {regressions}")
    print(f"\nsaved {out.relative_to(HERE)} (full transcripts inside; read the failures, don't just count them)")


if __name__ == "__main__":
    main()
