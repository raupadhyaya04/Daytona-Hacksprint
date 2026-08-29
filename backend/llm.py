"""Thin, normalized LLM client over Tensorix (OpenAI-compatible).

Both the real client and the mock return a `ChatResult`, so the agents never
touch provider-specific response objects.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

from config import settings


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResult:
    content: Optional[str]
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class LLMClient(Protocol):
    def chat(
        self,
        model: str,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> ChatResult: ...


class TensorixClient:
    """OpenAI SDK pointed at the Tensorix base URL, with simple retry."""

    def __init__(self) -> None:
        from openai import OpenAI  # lazy: mock mode needn't install openai

        if not settings.tensorix_api_key:
            raise RuntimeError(
                "TENSORIX_API_KEY is not set. Add it to backend/.env, or run with MOCK=1."
            )
        self._client = OpenAI(
            api_key=settings.tensorix_api_key,
            base_url=settings.tensorix_base_url,
        )

    def chat(
        self,
        model: str,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> ChatResult:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_err: Optional[Exception] = None
        for attempt in range(4):
            try:
                resp = self._client.chat.completions.create(**kwargs)
                return self._normalize(resp)
            except Exception as e:  # noqa: BLE001 - provider errors vary; retry a few times
                last_err = e
                # json_mode isn't universally supported; drop it and retry once cleanly.
                if json_mode and "response_format" in kwargs:
                    kwargs.pop("response_format", None)
                    continue
                time.sleep(min(2 ** attempt, 8))
        raise RuntimeError(f"Tensorix chat failed after retries: {last_err}")

    @staticmethod
    def _normalize(resp: Any) -> ChatResult:
        choice = resp.choices[0]
        msg = choice.message
        tool_calls: list[ToolCall] = []
        for tc in (getattr(msg, "tool_calls", None) or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except (json.JSONDecodeError, TypeError):
                args = {"_raw": getattr(tc.function, "arguments", "")}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        return ChatResult(
            content=msg.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
        )


def get_client() -> LLMClient:
    if settings.mock:
        from mock import MockLLM

        return MockLLM()
    return TensorixClient()


def extract_json(text: Optional[str]) -> dict:
    """Best-effort parse of a JSON object out of a model response."""
    if not text:
        return {}
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if 0 <= start < end:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return {}
