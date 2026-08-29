"""Batch / model-matrix runs.

Expand a spec (scenarios × defender models × attacker models × reps) into individual
runs, launch them, and let the global concurrency cap in `orchestrator` throttle how
many hold Daytona sandboxes at once. A batch is just a labelled set of run_ids; its
aggregate reuses `stats.compute_stats(run_ids=...)`.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional

from config import settings
from events import now_iso, store
from orchestrator import run_redteam
from scenarios import SCENARIOS
from stats import compute_stats


@dataclass
class BatchRecord:
    batch_id: str
    created_at: str
    status: str                     # running | completed
    spec: dict
    run_ids: list[str]
    cells: list[dict]               # [{scenario, defender_model, attacker_model, rep, run_id}]
    truncated: bool = False
    finished_at: Optional[str] = None

    def base(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "spec": self.spec,
            "run_ids": self.run_ids,
            "cells": self.cells,
            "truncated": self.truncated,
        }


class BatchManager:
    def __init__(self) -> None:
        self._batches: dict[str, BatchRecord] = {}
        self._tasks: set[asyncio.Task] = set()
        self._dir = settings.data_dir / "batches"
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── creation ────────────────────────────────────────────────────
    def create_batch(self, spec: dict) -> BatchRecord:
        scenarios = spec.get("scenarios") or []
        if not scenarios:
            raise ValueError("`scenarios` is required (a non-empty list).")
        bad = [s for s in scenarios if s not in SCENARIOS]
        if bad:
            raise ValueError(f"unknown scenarios: {bad}")

        defender_models = spec.get("defender_models") or [settings.defender_model]
        attacker_models = spec.get("attacker_models") or [settings.attacker_model]
        reps = max(1, min(int(spec.get("reps", 1)), 10))
        max_turns = spec.get("max_turns")
        early_stop = bool(spec.get("early_stop", True))

        cells: list[dict] = []
        for sc in scenarios:
            for dm in defender_models:
                for am in attacker_models:
                    for rep in range(reps):
                        cells.append({"scenario": sc, "defender_model": dm,
                                      "attacker_model": am, "rep": rep})
        truncated = False
        if len(cells) > settings.batch_max_runs:
            cells = cells[: settings.batch_max_runs]
            truncated = True

        batch_id = uuid.uuid4().hex[:10]
        run_ids: list[str] = []
        for c in cells:
            cfg: dict = {
                "scenario": c["scenario"],
                "models": {"defender": c["defender_model"], "attacker": c["attacker_model"]},
                "early_stop": early_stop,
                "batch_id": batch_id,
            }
            if max_turns is not None:
                cfg["max_turns"] = int(max_turns)
            rec = store.create_run(cfg)
            c["run_id"] = rec.run_id
            run_ids.append(rec.run_id)

        brec = BatchRecord(
            batch_id=batch_id, created_at=now_iso(), status="running",
            spec={"scenarios": scenarios, "defender_models": defender_models,
                  "attacker_models": attacker_models, "reps": reps,
                  "max_turns": max_turns, "early_stop": early_stop},
            run_ids=run_ids, cells=cells, truncated=truncated,
        )
        self._batches[batch_id] = brec
        self._persist(brec)

        run_tasks = [asyncio.create_task(run_redteam(rid)) for rid in run_ids]
        supervisor = asyncio.create_task(self._supervise(brec, run_tasks))
        self._tasks.add(supervisor)
        supervisor.add_done_callback(self._tasks.discard)
        return brec

    async def _supervise(self, brec: BatchRecord, tasks: list[asyncio.Task]) -> None:
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            brec.status = "completed"
            brec.finished_at = now_iso()
            self._persist(brec)

    # ── read ────────────────────────────────────────────────────────
    def get(self, batch_id: str) -> Optional[BatchRecord]:
        return self._batches.get(batch_id)

    def list(self) -> list[dict]:
        return [self._summary(b) for b in
                sorted(self._batches.values(), key=lambda b: b.created_at, reverse=True)]

    def _progress(self, brec: BatchRecord) -> dict:
        by_status: dict[str, int] = {}
        for rid in brec.run_ids:
            r = store.get(rid)
            st = r.status if r else "unknown"
            by_status[st] = by_status.get(st, 0) + 1
        done = sum(by_status.get(s, 0) for s in ("completed", "stopped", "failed"))
        return {"total": len(brec.run_ids), "done": done, "by_status": by_status}

    def _cells_with_results(self, brec: BatchRecord) -> list[dict]:
        out = []
        for c in brec.cells:
            r = store.get(c.get("run_id", ""))
            s = (r.summary if r else {}) or {}
            out.append({**c, "status": r.status if r else "unknown",
                        "breached": bool(s.get("breached")),
                        "first_breach_turn": s.get("first_breach_turn")})
        return out

    def _summary(self, brec: BatchRecord) -> dict:
        return {**brec.base(), "progress": self._progress(brec)}

    def detail(self, brec: BatchRecord) -> dict:
        return {
            **brec.base(),
            "progress": self._progress(brec),
            "cells": self._cells_with_results(brec),
            "stats": compute_stats(run_ids=brec.run_ids),
        }

    # ── persistence ─────────────────────────────────────────────────
    def _persist(self, brec: BatchRecord) -> None:
        try:
            (self._dir / f"{brec.batch_id}.json").write_text(json.dumps(brec.base(), indent=2))
        except OSError:
            pass

    def load_from_disk(self) -> int:
        count = 0
        for path in sorted(self._dir.glob("*.json")):
            try:
                d = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            bid = d.get("batch_id")
            if not bid or bid in self._batches:
                continue
            # Runs are restored (and interrupted ones marked failed) by store.load_from_disk;
            # a reloaded batch is treated as finished since its supervisor task is gone.
            self._batches[bid] = BatchRecord(
                batch_id=bid, created_at=d.get("created_at", now_iso()),
                status="completed", finished_at=d.get("finished_at"),
                spec=d.get("spec", {}), run_ids=d.get("run_ids", []),
                cells=d.get("cells", []), truncated=d.get("truncated", False),
            )
            count += 1
        return count


batches = BatchManager()
