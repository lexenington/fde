"""Terminal runner: asks the running simulator to run a checker and prints the result.

    docker compose exec sim python -m sim.checks integration
"""

import os
import sys

import httpx

ICON = {"pass": "PASS ", "fail": "FAIL ", "blocked": "BLOCK", "error": "ERROR"}


def main():
    lab = sys.argv[1] if len(sys.argv) > 1 else "integration"
    base = os.environ.get("SIM_URL", "http://localhost:8090")
    run = httpx.post(f"{base}/checks/{lab}/run", timeout=300).raise_for_status().json()
    section = None
    for r in run["results"]:
        if r["section"] != section:
            section = r["section"]
            print(f"\n{section}")
        print(f"  {ICON[r['status']]} {r['title']}  ({r['points']} pts)")
        if r["status"] != "pass":
            print(f"        {r['detail']}")
            print(f"        hint: {r['hint']}")
    print(f"\nScore: {run['score']}/{run['total']}  ({run['passed']}/{run['count']} checks)  saved as runs/{run['run_id']}.json")


if __name__ == "__main__":
    main()
