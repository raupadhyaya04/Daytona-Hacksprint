"""FastAPI app: start runs, list/inspect them, and stream events over SSE.

Run it:  uvicorn app:app --reload --port 8000
Mock:    MOCK=1 uvicorn app:app --port 8000     (no API keys needed)
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from batch import batches
from config import settings
from events import HEARTBEAT_TYPE, store
from orchestrator import run_redteam
from scenarios import SCENARIOS, list_scenarios
from stats import compute_stats

_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Restore run + batch history so listings and stats survive restarts.
    n_runs = store.load_from_disk()
    n_batches = batches.load_from_disk()
    if n_runs or n_batches:
        print(f"[startup] loaded {n_runs} run(s), {n_batches} batch(es) from disk")
    # Clean up any sandboxes left over from a previous crashed run.
    if not settings.mock and settings.daytona_configured:
        try:
            from sandboxes import reap_orphans

            n = await asyncio.to_thread(reap_orphans)
            if n:
                print(f"[startup] reaped {n} orphaned sandbox(es)")
        except Exception as e:  # noqa: BLE001
            print(f"[startup] orphan reap skipped: {e}")
    yield


app = FastAPI(title="Agent Red-Team Arena", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list(),
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    scenario: str
    max_turns: Optional[int] = None
    early_stop: Optional[bool] = True
    use_attacker_sandbox: Optional[bool] = None
    models: Optional[dict] = None


class BatchRequest(BaseModel):
    scenarios: list[str]
    defender_models: Optional[list[str]] = None
    attacker_models: Optional[list[str]] = None
    reps: Optional[int] = 1
    max_turns: Optional[int] = None
    early_stop: Optional[bool] = True


@app.get("/")
def root():
    return {"service": "Agent Red-Team Arena", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "mock": settings.mock,
        "tensorix_configured": settings.tensorix_configured,
        "daytona_configured": settings.daytona_configured,
        "models": {
            "attacker": settings.attacker_model,
            "defender": settings.defender_model,
            "judge": settings.judge_model,
        },
    }


@app.get("/api/scenarios")
def scenarios():
    return {"scenarios": list_scenarios()}


@app.get("/api/stats")
def stats(scenario: Optional[str] = None):
    return compute_stats(scenario=scenario)


@app.post("/api/batch")
async def create_batch(req: BatchRequest):
    if not settings.mock and not settings.tensorix_configured:
        raise HTTPException(status_code=400, detail="TENSORIX_API_KEY not set. Set it in backend/.env or run with MOCK=1.")
    try:
        brec = batches.create_batch(req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"batch_id": brec.batch_id, "status": brec.status,
            "run_ids": brec.run_ids, "truncated": brec.truncated}


@app.get("/api/batches")
def list_batches():
    return {"batches": batches.list()}


@app.get("/api/batch/{batch_id}")
def get_batch(batch_id: str):
    brec = batches.get(batch_id)
    if brec is None:
        raise HTTPException(status_code=404, detail="Batch not found.")
    return batches.detail(brec)


@app.post("/api/runs")
async def create_run(req: RunRequest):
    if req.scenario not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario '{req.scenario}'.")
    if not settings.mock and not settings.tensorix_configured:
        raise HTTPException(status_code=400, detail="TENSORIX_API_KEY not set. Set it in backend/.env or run with MOCK=1.")

    config: dict = {"scenario": req.scenario, "early_stop": bool(req.early_stop)}
    if req.max_turns is not None:
        config["max_turns"] = max(1, min(req.max_turns, 30))
    if req.use_attacker_sandbox is not None:
        config["use_attacker_sandbox"] = req.use_attacker_sandbox
    if req.models:
        config["models"] = req.models

    rec = store.create_run(config)
    task = asyncio.create_task(run_redteam(rec.run_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"run_id": rec.run_id, "status": rec.status}


@app.get("/api/runs")
def list_runs():
    return {"runs": store.list()}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    rec = store.get(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    store.ensure_events(run_id)   # hydrate from JSONL for runs reloaded after a restart
    return {**rec.public(), "events": rec.events}


@app.post("/api/runs/{run_id}/stop")
def stop_run(run_id: str):
    if store.get(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    ok = store.request_stop(run_id)
    return {"run_id": run_id, "stopping": ok}


@app.get("/api/runs/{run_id}/events")
async def stream_events(run_id: str):
    if store.get(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    async def gen():
        yield ": connected\n\n"
        async for d in store.subscribe(run_id):
            if d.get("type") == HEARTBEAT_TYPE:
                yield ": ping\n\n"
            else:
                yield f"data: {json.dumps(d)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
