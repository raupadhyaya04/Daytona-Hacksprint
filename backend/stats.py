"""Benchmark aggregation — turn many runs into leaderboard-ready stats.

Pure functions over the run store: attack-success rate per defender model and per
scenario, time-to-breach, breach categories, and rankings. This is what makes the
project an eval framework rather than a single-run demo.
"""
from __future__ import annotations

from typing import Iterable, Optional

from events import RunRecord, store

# Runs that actually produced a scoreable outcome (reached the turn loop).
SCORED_STATUSES = {"completed", "stopped"}


def _defender_model(rec: RunRecord) -> str:
    cfg = rec.config or {}
    return (
        (cfg.get("resolved_models") or {}).get("defender")
        or (cfg.get("models") or {}).get("defender")
        or "unknown"
    )


def _attacker_model(rec: RunRecord) -> str:
    cfg = rec.config or {}
    return (
        (cfg.get("resolved_models") or {}).get("attacker")
        or (cfg.get("models") or {}).get("attacker")
        or "unknown"
    )


def _scenario(rec: RunRecord) -> str:
    return (rec.config or {}).get("scenario", "unknown")


def _blank() -> dict:
    return {"runs": 0, "breaches": 0, "judge_flag_runs": 0, "first_breach_turns": [], "categories": {}}


def _add(bucket: dict, rec: RunRecord) -> None:
    s = rec.summary or {}
    bucket["runs"] += 1
    if s.get("breached"):
        bucket["breaches"] += 1
        if s.get("first_breach_turn") is not None:
            bucket["first_breach_turns"].append(s["first_breach_turn"])
    if s.get("judge_flags", 0):
        bucket["judge_flag_runs"] += 1
    for c in s.get("categories", []) or []:
        bucket["categories"][c] = bucket["categories"].get(c, 0) + 1


def _finalize(bucket: dict) -> dict:
    runs = bucket["runs"]
    fbt = bucket["first_breach_turns"]
    return {
        "runs": runs,
        "breaches": bucket["breaches"],
        "breach_rate": round(bucket["breaches"] / runs, 3) if runs else 0.0,
        "avg_first_breach_turn": round(sum(fbt) / len(fbt), 2) if fbt else None,
        "judge_flag_runs": bucket["judge_flag_runs"],
        "categories": bucket["categories"],
    }


def compute_stats(scenario: Optional[str] = None, run_ids: Optional[Iterable[str]] = None) -> dict:
    """Aggregate scored runs. Optionally filter to a scenario and/or a set of run_ids
    (the latter is how a batch reports its own aggregate)."""
    runs = store.records()
    if run_ids is not None:
        wanted = set(run_ids)
        runs = [r for r in runs if r.run_id in wanted]
    scored = [r for r in runs if r.status in SCORED_STATUSES]
    if scenario:
        scored = [r for r in scored if _scenario(r) == scenario]

    overall = _blank()
    by_def: dict[str, dict] = {}
    by_scn: dict[str, dict] = {}
    by_atk: dict[str, dict] = {}
    by_cell: dict[tuple[str, str], dict] = {}

    for r in scored:
        dm, am, sc = _defender_model(r), _attacker_model(r), _scenario(r)
        _add(overall, r)
        _add(by_def.setdefault(dm, _blank()), r)
        _add(by_scn.setdefault(sc, _blank()), r)
        _add(by_atk.setdefault(am, _blank()), r)
        _add(by_cell.setdefault((dm, sc), _blank()), r)

    matrix = [
        {"defender_model": dm, "scenario": sc, **_finalize(b)}
        for (dm, sc), b in sorted(by_cell.items())
    ]
    def_rows = [{"model": m, **_finalize(b)} for m, b in by_def.items()]
    atk_rows = [{"model": m, **_finalize(b)} for m, b in by_atk.items()]

    return {
        "total_runs": len(runs),
        "scored_runs": len(scored),
        "filters": {"scenario": scenario, "run_ids": list(run_ids) if run_ids is not None else None},
        "overall": _finalize(overall),
        "by_defender_model": {m: _finalize(b) for m, b in by_def.items()},
        "by_scenario": {s: _finalize(b) for s, b in by_scn.items()},
        "by_attacker_model": {m: _finalize(b) for m, b in by_atk.items()},
        "matrix": matrix,
        "leaderboard": {
            # most resistant = lowest breach rate; ties broken by more runs (more evidence)
            "most_resistant_defenders": sorted(def_rows, key=lambda r: (r["breach_rate"], -r["runs"])),
            # most effective = highest breach rate
            "most_effective_attackers": sorted(atk_rows, key=lambda r: (-r["breach_rate"], -r["runs"])),
        },
    }
