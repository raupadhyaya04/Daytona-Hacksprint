"""Runtime configuration, loaded from environment / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except Exception:  # dotenv is optional; env vars may be set another way
    pass


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip())
    except (ValueError, AttributeError):
        return default


@dataclass
class Settings:
    tensorix_api_key: str = field(default_factory=lambda: os.getenv("TENSORIX_API_KEY", "").strip())
    tensorix_base_url: str = field(
        default_factory=lambda: os.getenv("TENSORIX_BASE_URL", "https://api.tensorx.ai/v1").strip()
    )
    daytona_api_key: str = field(default_factory=lambda: os.getenv("DAYTONA_API_KEY", "").strip())

    attacker_model: str = field(default_factory=lambda: os.getenv("ATTACKER_MODEL", "z-ai/glm-5.2").strip())
    defender_model: str = field(default_factory=lambda: os.getenv("DEFENDER_MODEL", "z-ai/glm-5.2").strip())
    judge_model: str = field(default_factory=lambda: os.getenv("JUDGE_MODEL", "z-ai/glm-5.2").strip())

    mock: bool = field(default_factory=lambda: _bool("MOCK", False))
    use_attacker_sandbox: bool = field(default_factory=lambda: _bool("USE_ATTACKER_SANDBOX", True))

    max_turns: int = field(default_factory=lambda: _int("MAX_TURNS", 8))
    max_tool_calls_per_turn: int = field(default_factory=lambda: _int("MAX_TOOL_CALLS_PER_TURN", 4))
    run_timeout_sec: int = field(default_factory=lambda: _int("RUN_TIMEOUT_SEC", 300))
    sandbox_exec_timeout: int = field(default_factory=lambda: _int("SANDBOX_EXEC_TIMEOUT", 30))

    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "./data")).resolve())
    cors_origins: str = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*").strip())

    def cors_list(self) -> list[str]:
        if self.cors_origins == "*" or not self.cors_origins:
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def tensorix_configured(self) -> bool:
        return bool(self.tensorix_api_key)

    @property
    def daytona_configured(self) -> bool:
        return bool(self.daytona_api_key)


settings = Settings()
