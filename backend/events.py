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
TERMINAL_STATUSES = {"completed", "failed", "stopped"}
HEARTBEAT_TYPE = "__heartbeat__"   # internal sentinel; rendered as an SSE comment


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

    def records(self) -> list[RunRecord]:
        return list(self._runs.values())

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
        """Yield the full history, then live events (with periodic heartbeats),
        until a terminal event or a terminal run status."""
        rec = self._runs.get(run_id)
        if rec is None:
            return
        self.ensure_events(run_id)
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
            # A reloaded/finished run has no live task feeding the queue — don't hang.
            if rec.status in TERMINAL_STATUSES:
                return
            while True:
                try:
                    d = await asyncio.wait_for(q.get(), timeout=settings.heartbeat_sec)
                except asyncio.TimeoutError:
                    yield {"type": HEARTBEAT_TYPE}
                    continue
                if d["seq"] <= last_seq:
                    continue
                last_seq = d["seq"]
                yield d
                if d["type"] in TERMINAL_TYPES:
                    return
        finally:
            self._subscribers.get(run_id, set()).discard(q)

    def ensure_events(self, run_id: str) -> None:
        """Lazily hydrate a run's events from its JSONL file (for reloaded runs)."""
        rec = self._runs.get(run_id)
        if rec is None or rec.events:
            return
        path = self._dir / f"{run_id}.jsonl"
        if not path.exists():
            return
        events: list[dict] = []
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            return
        rec.events = events

    def load_from_disk(self) -> int:
        """Rebuild the in-memory registry from persisted run metadata so history and
        stats survive restarts. Events hydrate lazily; runs left mid-flight by a
        previous crash are marked failed."""
        count = 0
        for meta_path in sorted(self._dir.glob("*.meta.json")):
            try:
                d = json.loads(meta_path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            run_id = d.get("run_id")
            if not run_id or run_id in self._runs:
                continue
            status = d.get("status", "failed")
            if status in ("provisioning", "running"):
                status = "failed"   # its orchestrator task died with the old process
            rec = RunRecord(
                run_id=run_id,
                status=status,
                created_at=d.get("created_at", now_iso()),
                finished_at=d.get("finished_at"),
                config=d.get("config", {}) or {},
                sandboxes=d.get("sandboxes", {}) or {},
                summary=d.get("summary", {}) or {},
            )
            self._runs[run_id] = rec
            self._subscribers.setdefault(run_id, set())
            self._stops.setdefault(run_id, asyncio.Event())
            count += 1
        return count

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
