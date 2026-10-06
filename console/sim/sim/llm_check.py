"""First contact with the real Claude API: does every feature that depends on it actually work?

    docker compose exec sim python -m sim.llm_check

It runs one short, real stakeholder call (two questions, then the debrief) and one inject-card review, in throwaway
folders, so nothing is saved into your repo. It costs a few cents. Run it once after exporting ANTHROPIC_API_KEY, and
again after changing FDE_CHAT_MODEL or FDE_JUDGE_MODEL.
"""

import sys
import tempfile
import time
from pathlib import Path

from . import config, injects, llm, stakeholders


def _stage(name, fn):
    t0 = time.perf_counter()
    try:
        detail = fn()
        print(f"  PASS  {name}  ({time.perf_counter() - t0:.1f}s)" + (f"\n        {detail}" if detail else ""))
        return True
    except llm.LLMUnavailable as e:
        print(f"  FAIL  {name}\n        {e}")
    except Exception as e:     # a schema or logic problem, not an outage: show the type so it can be reported
        print(f"  FAIL  {name}\n        {type(e).__name__}: {e}")
    return False


def run() -> bool:
    print(f"Chat model:  {llm.CHAT_MODEL}\nJudge model: {llm.JUDGE_MODEL}\n")
    if not llm.configured():
        print("ANTHROPIC_API_KEY is not set in this container. Export it where you run `docker compose up`, then `docker compose up -d sim`.")
        return False

    saved = (config.PRACTICE_DIR, config.LABS_DIR)
    try:
        return _run()
    finally:
        config.PRACTICE_DIR, config.LABS_DIR = saved


def _run() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        config.PRACTICE_DIR = Path(tmp) / "practice"
        config.LABS_DIR = Path(tmp) / "labs"
        state = {}

        def call():
            scen = stakeholders.scenarios()[0]
            char = scen["characters"][0]
            view = stakeholders.start(scen["scenario"], char["id"])
            state["sid"] = view["session_id"] if "session_id" in view else view["id"]
            v1 = stakeholders.say(state["sid"], "Thanks for making time. Before we get into any solution: walk me through the last time this problem actually happened.")
            v2 = stakeholders.say(state["sid"], "And who else has to be happy before this goes live?")
            them = [m for m in v2["messages"] if m["who"] == "them"]
            assert len(them) >= 3 and all(m["text"].strip() for m in them), "an empty reply came back"
            return f"{char['name']} answered twice"

        def debrief():
            r = stakeholders.end(state["sid"])
            assert len(r["dimensions"]) == 6, f"expected 6 scored dimensions, got {len(r['dimensions'])}"
            assert all(1 <= d["score"] <= 5 for d in r["dimensions"]), "a score was out of range"
            assert r["verdict"].strip() and r["next_time"], "verdict or next_time was empty"
            return f"average {r['average']}/5, discovery {r['discovery_pct']}%, talk ratio {r['talk_ratio']}"

        def card():
            c = injects.draw("integration")
            r = injects.respond("integration", c["id"],
                                "Thanks for flagging this. Short version: we are not going to miss the date, and here is exactly what changes. "
                                "I will confirm the new limit with your team today, adjust our client to back off on 429s, and send you a one-line status tomorrow morning.")
            fb = r["feedback"]
            assert fb and 1 <= fb["rating"] <= 5 and fb["sharper_sentence"].strip(), "feedback was missing or malformed"
            return f"card {c['id']}: rating {fb['rating']}/5"

        results = [_stage("A stakeholder answers in character (2 turns)", call)]
        results.append(_stage("The judge scores the call (6 dimensions, valid ranges)", debrief) if results[0] else False)
        results.append(_stage("An inject-card reply gets structured feedback", card))
    ok = all(results)
    print("\nAll good." if ok else "\nSomething failed. The message above says what; if it is a schema or cut-off problem, that is a bug in the Console, not in your setup.")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
