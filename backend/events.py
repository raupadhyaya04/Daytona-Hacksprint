"""Event model + run records + an async pub/sub store backing the SSE stream.

Everything that happens in a run is a single flat `Event`. The frontend renders
the run as a timeline of these events, so there is exactly one shape to learn.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from config import settings

# Event `type` values (all lower_snake):
#   run_started    - a run began; meta has scenario/config
#   status         - lifecycle note (provisioning, sandboxes ready, teardown, ...)
#   message        - a chat message from attacker or defender (content = text)
#   tool_call      - an agent invoked a tool (tool = {name, input})
#   tool_result    - result of a tool call (output = {stdout, exit_code})
#   verdict        - the judge scored an exchange (verdict = {...})
#   breach         - a deterministic detector confirmed a breach (verdict = {...})
#   run_finished   - terminal success (meta = summary)
#   error          - terminal failure (content = message)

TERMINAL_TYPES = {"run_finished", "error"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Event:
    run_id: str
    seq: int = 0
    ts: str = field(default_factory=now_iso)
    turn: int = 0
    actor: str = "system"          # attacker | defender | judge | system
    type: str = "status"
    content: Optional[str] = None
    tool: Optional[dict] = None    # {name, input}
    output: Optional[dict] = None  # {stdout, exit_code}
    sandbox: Optional[str] = None  # attacker | defender
    verdict: Optional[dict] = None # {breached, severity, category, rationale, source, evidence}
    meta: Optional[dict] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None or k in ("content",)}


@dataclass
class RunRecord:
    run_id: str
    status: str = "provisioning"   # provisioning | running | completed | failed | stopped
    created_at: str = field(default_factory=now_iso)
    finished_at: Optional[str] = None
    config: dict = field(default_factory=dict)
    sandboxes: dict = field(default_factory=dict)   # {attacker: id|None, defender: id}
    events: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=lambda: {
        "breached": False,
        "breach_count": 0,
        "first_breach_turn": None,
        "turns_run": 0,
        "categories": [],
    })

    def public(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "config": self.config,
            "sandboxes": self.sandboxes,
            "summary": self.summary,
        }


class RunStore:
    """Holds runs in memory, persists events to JSONL, and fans events out to
    any number of live SSE subscribers."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._stops: dict[str, asyncio.Event] = {}
        self._dir = settings.data_dir / "runs"
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── run lifecycle ───────────────────────────────────────────────
    def create_run(self, config: dict) -> RunRecord:
        run_id = uuid.uuid4().hex[:12]
        rec = RunRecord(run_id=run_id, config=config)
        self._runs[run_id] = rec
        self._subscribers[run_id] = set()
        self._stops[run_id] = asyncio.Event()
        self._persist_meta(rec)
        return rec

    def get(self, run_id: str) -> Optional[RunRecord]:
        return self._runs.get(run_id)

    def list(self) -> list[dict]:
        return [r.public() for r in sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)]

    def stop_flag(self, run_id: str) -> Optional[asyncio.Event]:
        return self._stops.get(run_id)

    def request_stop(self, run_id: str) -> bool:
        ev = self._stops.get(run_id)
        if ev is None:
            return False
        ev.set()
        return True

    def set_status(self, run_id: str, status: str) -> None:
        rec = self._runs.get(run_id)
        if rec:
            rec.status = status
            if status in ("completed", "failed", "stopped"):
                rec.finished_at = now_iso()
            self._persist_meta(rec)

    # ── events ──────────────────────────────────────────────────────
    def append(self, event: Event) -> Event:
        rec = self._runs.get(event.run_id)
        if rec is None:
            return event
        event.seq = len(rec.events)
        d = event.to_dict()
        rec.events.append(d)
        self._persist_event(event.run_id, d)
        for q in list(self._subscribers.get(event.run_id, ())):
            try:
                q.put_nowait(d)
            except asyncio.QueueFull:
                pass
        return event

    async def subscribe(self, run_id: str) -> AsyncIterator[dict]:
        """Yield the full history, then live events, until a terminal event."""
        rec = self._runs.get(run_id)
        if rec is None:
            return
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subscribers.setdefault(run_id, set()).add(q)
        try:
            snapshot = list(rec.events)
            last_seq = -1
            for d in snapshot:
                last_seq = d["seq"]
                yield d
                if d["type"] in TERMINAL_TYPES:
                    return
            while True:
                d = await q.get()
                if d["seq"] <= last_seq:
                    continue
                last_seq = d["seq"]
                yield d
                if d["type"] in TERMINAL_TYPES:
                    return
        finally:
            self._subscribers.get(run_id, set()).discard(q)

    # ── persistence ─────────────────────────────────────────────────
    def _persist_event(self, run_id: str, d: dict) -> None:
        try:
            with (self._dir / f"{run_id}.jsonl").open("a") as f:
                f.write(json.dumps(d) + "\n")
        except OSError:
            pass

    def _persist_meta(self, rec: RunRecord) -> None:
        try:
            (self._dir / f"{rec.run_id}.meta.json").write_text(json.dumps(rec.public(), indent=2))
        except OSError:
            pass


store = RunStore()
