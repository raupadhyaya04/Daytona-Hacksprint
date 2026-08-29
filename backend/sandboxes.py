"""Sandbox provisioning and command execution.

Real runs use Daytona (each agent gets its own isolated sandbox). Mock runs use
an in-process fake with a tiny filesystem + command interpreter so the exact same
orchestrator code path works with no keys and no network.
"""
from __future__ import annotations

import base64
import os
import shlex
from dataclasses import dataclass
from typing import Optional, Protocol

from config import settings

APP_LABEL = "redteam-arena"


@dataclass
class ExecResult:
    exit_code: int
    stdout: str


class Sandbox(Protocol):
    id: str
    role: str

    def exec(self, command: str) -> ExecResult: ...
    def write_file(self, path: str, content: str) -> None: ...
    def close(self) -> None: ...


# ── Daytona (real) ──────────────────────────────────────────────────
_daytona = None


def _get_daytona():
    global _daytona
    if _daytona is None:
        from daytona import Daytona, DaytonaConfig  # lazy import

        if not settings.daytona_api_key:
            raise RuntimeError(
                "DAYTONA_API_KEY is not set. Add it to backend/.env, or run with MOCK=1."
            )
        _daytona = Daytona(DaytonaConfig(api_key=settings.daytona_api_key))
    return _daytona


class DaytonaSandbox:
    def __init__(self, sandbox, role: str) -> None:
        self._sb = sandbox
        self.id = getattr(sandbox, "id", "unknown")
        self.role = role

    def exec(self, command: str) -> ExecResult:
        resp = self._sb.process.exec(command, timeout=settings.sandbox_exec_timeout)
        stdout = getattr(resp, "result", None)
        if stdout is None:
            artifacts = getattr(resp, "artifacts", None)
            stdout = getattr(artifacts, "stdout", "") if artifacts else ""
        return ExecResult(exit_code=getattr(resp, "exit_code", 0) or 0, stdout=stdout or "")

    def write_file(self, path: str, content: str) -> None:
        _plant_file(self, path, content)

    def close(self) -> None:
        try:
            _get_daytona().delete(self._sb)
        except Exception:
            pass


def _provision_daytona(role: str, run_id: str, env_secrets: dict, planted_files: dict) -> DaytonaSandbox:
    from daytona import CreateSandboxFromSnapshotParams

    daytona = _get_daytona()
    params = CreateSandboxFromSnapshotParams(
        env_vars=dict(env_secrets),
        labels={"app": APP_LABEL, "run": run_id, "role": role},
    )
    sb = daytona.create(params, timeout=120)
    wrapper = DaytonaSandbox(sb, role)
    for path, content in planted_files.items():
        _plant_file(wrapper, path, content)
    return wrapper


def _plant_file(sb: DaytonaSandbox, path: str, content: str) -> None:
    """Write a file into the sandbox. Paths starting with '~/' are planted in the
    sandbox user's HOME (which it owns and can read) rather than an absolute path
    like /root — the sandbox runs as a non-root user, so /root is unreadable and
    unwritable, which would break both planting and the guardrail test itself."""
    b64 = base64.b64encode(content.encode()).decode()
    if path.startswith("~/"):
        rel = path[2:]
        parent = os.path.dirname(rel)
        mkdir = f'mkdir -p "$HOME"/{shlex.quote(parent)}' if parent else "true"
        target = f'"$HOME"/{shlex.quote(rel)}'
    else:
        parent = path.rsplit("/", 1)[0] or "/"
        mkdir = f"mkdir -p {shlex.quote(parent)}"
        target = shlex.quote(path)
    sb.exec(f"{mkdir} && echo {shlex.quote(b64)} | base64 -d > {target}")


def reap_orphans() -> int:
    """Delete any sandboxes left over from crashed runs (matched by our label)."""
    try:
        from daytona import ListSandboxesQuery

        daytona = _get_daytona()
        count = 0
        for sb in daytona.list(ListSandboxesQuery(labels={"app": APP_LABEL})):
            try:
                daytona.delete(sb)
                count += 1
            except Exception:
                pass
        return count
    except Exception:
        return 0


# ── Mock (in-process) ───────────────────────────────────────────────
class MockSandbox:
    """A believable fake: an in-memory filesystem + a handful of interpreted
    commands. Enough for the scripted mock run to demonstrate a real breach."""

    _counter = 0

    def __init__(self, role: str, run_id: str, env_secrets: dict, planted_files: dict) -> None:
        MockSandbox._counter += 1
        self.id = f"mock-{role}-{run_id}-{MockSandbox._counter}"
        self.role = role
        self._env = dict(env_secrets)
        self._fs = {self._norm(p): c for p, c in planted_files.items()}

    @staticmethod
    def _norm(path: str) -> str:
        return path.replace("~", "/root")

    def exec(self, command: str) -> ExecResult:
        cmd = command.strip()
        try:
            parts = shlex.split(cmd)
        except ValueError:
            parts = cmd.split()
        head = parts[0] if parts else ""

        # destructive commands "succeed" (so destructive-ops breach = executed)
        destructive = ("rm", "dd", "mkfs", "shred", "mkswap")
        if head in destructive or ":(){" in cmd or ":|:&" in cmd:
            return ExecResult(0, "")

        if head == "cat" and len(parts) >= 2:
            content = self._fs.get(self._norm(parts[1]))
            if content is None:
                return ExecResult(1, f"cat: {parts[1]}: No such file or directory\n")
            return ExecResult(0, content)

        if head in ("env", "printenv"):
            return ExecResult(0, "".join(f"{k}={v}\n" for k, v in self._env.items()))

        if head == "whoami":
            return ExecResult(0, "root\n")

        if head == "ls":
            target = self._norm(parts[1]) if len(parts) >= 2 else "/root"
            names = sorted({
                p[len(target):].lstrip("/").split("/")[0]
                for p in self._fs
                if p.startswith(target.rstrip("/") + "/")
            })
            return ExecResult(0, "\n".join(names) + ("\n" if names else ""))

        if head == "echo":
            return ExecResult(0, " ".join(parts[1:]) + "\n")

        # Unknown-but-harmless: pretend it ran.
        return ExecResult(0, "")

    def write_file(self, path: str, content: str) -> None:
        self._fs[self._norm(path)] = content

    def close(self) -> None:
        return None


# ── Factory ─────────────────────────────────────────────────────────
def provision(role: str, run_id: str, env_secrets: dict, planted_files: dict) -> Sandbox:
    if settings.mock:
        return MockSandbox(role, run_id, env_secrets, planted_files)
    return _provision_daytona(role, run_id, env_secrets, planted_files)
