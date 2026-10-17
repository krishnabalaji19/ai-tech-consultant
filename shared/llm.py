"""One place for LLM calls. Provider and model come from .env. Never log keys."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")


class LLMError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    max_retries: int
    retry_base_seconds: float
    timeout_seconds: float


def load_llm_settings() -> LLMSettings:
    provider = (os.getenv("LLM_PROVIDER") or "gemini").strip().lower()
    if provider == "claude":
        model = os.getenv("CLAUDE_MODEL") or "claude-sonnet-4-5"
    else:
        model = os.getenv("GEMINI_MODEL") or "gemini-3.5-flash-lite"
    return LLMSettings(
        provider=provider,
        model=model,
        max_retries=int(os.getenv("LLM_MAX_RETRIES") or "3"),
        retry_base_seconds=float(os.getenv("LLM_RETRY_BASE_SECONDS") or "1.0"),
        timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS") or "45"),
    )


def _gemini_key() -> str:
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        raise LLMError("GEMINI_API_KEY is missing in .env", retryable=False)
    return key


def _anthropic_key() -> str:
    key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise LLMError("ANTHROPIC_API_KEY is missing in .env", retryable=False)
    return key


def _extract_gemini_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        feedback = payload.get("promptFeedback") or {}
        reason = feedback.get("blockReason") or "empty model response"
        raise LLMError(f"Gemini returned no answer ({reason})", retryable=False)
    parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
    text = "".join(str(part.get("text") or "") for part in parts).strip()
    if not text:
        raise LLMError("Gemini returned an empty answer", retryable=False)
    return text


def _extract_claude_text(payload: dict) -> str:
    blocks = payload.get("content") or []
    text = "".join(
        str(block.get("text") or "") for block in blocks if block.get("type") == "text"
    ).strip()
    if not text:
        raise LLMError("Claude returned an empty answer", retryable=False)
    return text


class LLMClient:
    def __init__(self, settings: LLMSettings | None = None) -> None:
        self.settings = settings or load_llm_settings()

    async def generate(self, *, system: str, user: str) -> str:
        last_error: LLMError | None = None
        attempts = max(1, self.settings.max_retries)
        for attempt in range(attempts):
            try:
                return await self._once(system=system, user=user)
            except LLMError as exc:
                last_error = exc
                if not exc.retryable or attempt == attempts - 1:
                    raise
                await asyncio.sleep(self.settings.retry_base_seconds * (2**attempt))
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = LLMError(
                    "The language model timed out or could not be reached.",
                    retryable=True,
                )
                if attempt == attempts - 1:
                    raise last_error from exc
                await asyncio.sleep(self.settings.retry_base_seconds * (2**attempt))
        raise last_error or LLMError("The language model failed.", retryable=False)

    async def _once(self, *, system: str, user: str) -> str:
        if self.settings.provider == "claude":
            return await self._claude(system=system, user=user)
        return await self._gemini(system=system, user=user)

    async def _gemini(self, *, system: str, user: str) -> str:
        key = _gemini_key()
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.model}:generateContent"
        )
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.1},
        }
        timeout = httpx.Timeout(self.settings.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, params={"key": key}, json=body)
        if response.status_code == 429 or response.status_code >= 500:
            raise LLMError(
                "Gemini is busy or rate-limited. Try again in a minute.",
                retryable=True,
            )
        if response.status_code >= 400:
            raise LLMError(
                f"Gemini rejected the request (HTTP {response.status_code}).",
                retryable=False,
            )
        return _extract_gemini_text(response.json())

    async def _claude(self, *, system: str, user: str) -> str:
        key = _anthropic_key()
        timeout = httpx.Timeout(self.settings.timeout_seconds)
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.settings.model,
            "max_tokens": 800,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "temperature": 0.1,
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body,
            )
        if response.status_code == 429 or response.status_code >= 500:
            raise LLMError(
                "Claude is busy or rate-limited. Try again in a minute.",
                retryable=True,
            )
        if response.status_code >= 400:
            raise LLMError(
                f"Claude rejected the request (HTTP {response.status_code}).",
                retryable=False,
            )
        return _extract_claude_text(response.json())
