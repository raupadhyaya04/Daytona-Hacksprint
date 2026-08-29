"""The run loop: provision two sandboxes, run attacker↔defender for N turns,
score every exchange (deterministic + judge), stream events, always tear down.
"""
from __future__ import annotations

import asyncio

from agents import Attacker, Defender, Judge
from config import settings
from detectors import SEVERITY_ORDER, detect, worst_severity
from events import Event, store
from llm import get_client
from sandboxes import Sandbox, provision
from scenarios import get_scenario, new_secret


def _make_emit(run_id: str):
    def emit(actor: str, type: str, *, turn: int = 0, content=None, tool=None,
             output=None, sandbox=None, verdict=None, meta=None) -> None:
        store.append(Event(
            run_id=run_id, turn=turn, actor=actor, type=type, content=content,
            tool=tool, output=output, sandbox=sandbox, verdict=verdict, meta=meta,
        ))
    return emit


async def run_redteam(run_id: str) -> None:
    rec = store.get(run_id)
    if rec is None:
        return
    emit = _make_emit(run_id)
    cfg = rec.config
    stop = store.stop_flag(run_id)

    scenario = get_scenario(cfg["scenario"])
    max_turns = int(cfg.get("max_turns", settings.max_turns))
    early_stop = bool(cfg.get("early_stop", True))
    use_attacker_sandbox = bool(cfg.get("use_attacker_sandbox", settings.use_attacker_sandbox))
    models = cfg.get("models", {})
    a_model = models.get("attacker", settings.attacker_model)
    d_model = models.get("defender", settings.defender_model)
    j_model = models.get("judge", settings.judge_model)

    secret = new_secret()
    sandboxes: list[Sandbox] = []
    torn_down = False

    def teardown() -> None:
        nonlocal torn_down
        if torn_down:
            return
        torn_down = True
        emit("system", "status", content="Tearing down sandboxes.")
        for sb in sandboxes:
            try:
                sb.close()
            except Exception:
                pass

    try:
        emit("system", "run_started", meta={
            "scenario": scenario.id, "scenario_name": scenario.name,
            "attacker_goal": scenario.attacker_goal, "max_turns": max_turns,
            "models": {"attacker": a_model, "defender": d_model, "judge": j_model},
            "mock": settings.mock,
        })

        # ── provision ────────────────────────────────────────────────
        emit("system", "status", content="Provisioning defender sandbox…")
        try:
            defender_sb = await asyncio.to_thread(
                provision, "defender", run_id,
                scenario.env_secrets(secret), scenario.planted_files(secret),
            )
        except Exception as e:  # noqa: BLE001
            store.set_status(run_id, "failed")
            emit("system", "error", content=f"Failed to provision defender sandbox: {e}")
            return
        sandboxes.append(defender_sb)
        rec.sandboxes["defender"] = defender_sb.id

        attacker_sb = None
        if use_attacker_sandbox:
            emit("system", "status", content="Provisioning attacker sandbox…")
            try:
                attacker_sb = await asyncio.to_thread(provision, "attacker", run_id, {}, {})
                sandboxes.append(attacker_sb)
                rec.sandboxes["attacker"] = attacker_sb.id
            except Exception as e:  # noqa: BLE001
                emit("system", "status", content=f"Attacker sandbox unavailable ({e}); attacker will run tool-free.")
        store._persist_meta(rec)
        emit("system", "status", content="Sandboxes ready.", meta={"sandboxes": rec.sandboxes})

        # ── agents ───────────────────────────────────────────────────
        client = get_client()
        attacker = Attacker(client, a_model, scenario.attacker_goal, attacker_sb)
        defender = Defender(client, d_model, scenario.defender_rules, defender_sb)
        judge = Judge(client, j_model)

        store.set_status(run_id, "running")
        transcript: list[dict] = []
        loop = asyncio.get_event_loop()
        deadline = loop.time() + settings.run_timeout_sec

        for turn in range(1, max_turns + 1):
            if stop and stop.is_set():
                store.set_status(run_id, "stopped")
                emit("system", "status", content="Run stopped by user.", turn=turn)
                break
            if loop.time() > deadline:
                emit("system", "status", content="Run wall-clock timeout reached.", turn=turn)
                break

            # attacker speaks
            attacker_msg = await attacker.next_message(transcript, turn, emit)
            emit("attacker", "message", turn=turn, content=attacker_msg)

            # defender responds (may execute commands in its sandbox)
            defender_msg, executed = await defender.respond(transcript, attacker_msg, turn, emit)
            emit("defender", "message", turn=turn, content=defender_msg)

            transcript.append({"speaker": "attacker", "content": attacker_msg})
            transcript.append({"speaker": "defender", "content": defender_msg})

            # deterministic detection (ground truth)
            findings = detect(defender_msg, executed, secret, scenario.extra_blocklist)
            for f in findings:
                emit("system", "breach", turn=turn, verdict=f.as_verdict(),
                     content=f.evidence)
            if findings:
                s = rec.summary
                s["breached"] = True
                s["breach_count"] += len(findings)
                if s["first_breach_turn"] is None:
                    s["first_breach_turn"] = turn
                for f in findings:
                    if f.category not in s["categories"]:
                        s["categories"].append(f.category)

            # judge (softer policy read)
            verdict = await judge.evaluate(attacker_msg, defender_msg, executed, turn, emit)
            if verdict.get("breached"):
                rec.summary["judge_flags"] = rec.summary.get("judge_flags", 0) + 1

            rec.summary["turns_run"] = turn
            store._persist_meta(rec)

            # early stop on a serious confirmed breach
            if early_stop and findings and SEVERITY_ORDER.get(worst_severity(findings), 0) >= SEVERITY_ORDER["high"]:
                emit("system", "status", turn=turn, content="High-severity breach confirmed; stopping early.")
                break

        if store.get(run_id).status not in ("stopped",):
            store.set_status(run_id, "completed")

        teardown()
        emit("system", "run_finished", meta={**rec.summary, "status": store.get(run_id).status})

    except asyncio.CancelledError:
        store.set_status(run_id, "stopped")
        teardown()
        emit("system", "error", content="Run cancelled.")
        raise
    except Exception as e:  # noqa: BLE001
        store.set_status(run_id, "failed")
        teardown()
        emit("system", "error", content=f"Run failed: {e}")
    finally:
        teardown()
