"""Seed a RUNNING backend with a demo batch so /api/stats, the leaderboard, and the
sign-off report populate immediately — a demo fallback and a data source for the frontend.

This POSTs to the live server (rather than running its own in-process store), so it works
against a server that's already up — no restart needed. Point it at a MOCK server for a
free, differentiated APPROVED/REJECTED leaderboard.

    # terminal 1
    MOCK=1 python main.py
    # terminal 2
    python seed_demo.py

Override the target with SEED_API_BASE (default http://localhost:8000). Against a LIVE
(non-mock) server this would launch real runs, so it refuses unless SEED_ALLOW_LIVE=1.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_BASE = os.getenv("SEED_API_BASE", "http://localhost:8000").rstrip("/")

SCENARIOS = ["poisoned-task", "aws-creds", "secret-flag"]
DEFENDER_MODELS = [
    "z-ai/glm-5.2",                     # breaches (REJECTED in mock)
    "deepseek/deepseek-v4-flash-0731",  # breaches (REJECTED in mock)
    "minimax/minimax-m2",               # resists  (APPROVED in mock)
    "z-ai/glm-5.1",                     # resists  (APPROVED in mock)
]
REPS = 2


def _get(path: str) -> dict:
    with urllib.request.urlopen(API_BASE + path, timeout=30) as r:
        return json.loads(r.read())


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        API_BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> None:
    try:
        health = _get("/api/health")
    except urllib.error.URLError as e:
        sys.exit(f"Can't reach the backend at {API_BASE} ({e.reason}).\n"
                 f"Start it first, e.g.:  MOCK=1 python main.py")

    total = len(SCENARIOS) * len(DEFENDER_MODELS) * REPS
    if not health.get("mock") and os.getenv("SEED_ALLOW_LIVE") != "1":
        sys.exit(
            f"The server at {API_BASE} is in LIVE mode — seeding would launch {total} real "
            "runs (Tensorix + Daytona cost).\nStart the backend with MOCK=1 for the free demo, "
            "or set SEED_ALLOW_LIVE=1 to proceed anyway."
        )

    resp = _post("/api/batch", {
        "scenarios": SCENARIOS, "defender_models": DEFENDER_MODELS,
        "reps": REPS, "max_turns": 4,
    })
    batch_id = resp["batch_id"]
    n = len(resp.get("run_ids", []))
    print(f"seeding batch {batch_id}: {n} runs against {API_BASE}"
          + (" [TRUNCATED by BATCH_MAX_RUNS]" if resp.get("truncated") else ""), flush=True)

    while True:
        b = _get(f"/api/batch/{batch_id}")
        prog = b.get("progress", {})
        if b.get("status") == "completed":
            break
        print(f"  {prog.get('done', 0)}/{prog.get('total', n)} done…", flush=True)
        time.sleep(1)

    report = _get("/api/report")
    print("done — /api/stats and /api/report are now populated.\n", flush=True)
    print(report["markdown"])


if __name__ == "__main__":
    main()
