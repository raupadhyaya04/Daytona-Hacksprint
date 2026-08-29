"""Seed the benchmark with a full MOCK batch so /api/stats, the leaderboard, and the
sign-off report are populated instantly — a reliable demo fallback (stage wifi dies)
and a data source the frontend can build against with no keys.

    python seed_demo.py

Runs entirely in mock mode (no Tensorix / Daytona keys, no network). A couple of the
defender models are "hardened" in mock, so the leaderboard shows a real APPROVED/REJECTED
split instead of a flat 100%.
"""
import os

os.environ["MOCK"] = "1"   # force mock regardless of .env, before settings load

import asyncio

from batch import batches
from stats import build_report

# Headline scenario first. A mix of models that breach vs. resist in mock (see mock.RESISTANT_MODELS).
SCENARIOS = ["poisoned-task", "aws-creds", "secret-flag"]
DEFENDER_MODELS = [
    "z-ai/glm-5.2",                     # breaches (REJECTED)
    "deepseek/deepseek-v4-flash-0731",  # breaches (REJECTED)
    "minimax/minimax-m2",               # resists  (APPROVED)
    "z-ai/glm-5.1",                     # resists  (APPROVED)
]


async def main() -> None:
    brec = batches.create_batch({
        "scenarios": SCENARIOS,
        "defender_models": DEFENDER_MODELS,
        "reps": 2,
        "max_turns": 4,
    })
    print(f"seeding batch {brec.batch_id}: {len(brec.run_ids)} runs "
          f"({len(SCENARIOS)} scenarios x {len(DEFENDER_MODELS)} models x 2 reps)"
          + (" [TRUNCATED by BATCH_MAX_RUNS]" if brec.truncated else ""))
    while batches.get(brec.batch_id).status != "completed":
        await asyncio.sleep(0.1)
    print("done — /api/stats and /api/report are now populated.\n")
    print(build_report()["markdown"])


if __name__ == "__main__":
    asyncio.run(main())
