"""LLM retry tests. No live Gemini key is used."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TASK1_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TASK1_ROOT.parent
sys.path.insert(0, str(TASK1_ROOT))
sys.path.insert(0, str(REPO_ROOT))

import httpx

from shared.llm import LLMClient, LLMError, LLMSettings


class FakeAsyncClient:
    calls = 0

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def post(self, *args, **kwargs) -> httpx.Response:
        type(self).calls += 1
        return httpx.Response(429, json={"error": "busy"})


class LlmRetryTests(unittest.TestCase):
    def test_retries_429_then_returns_error(self) -> None:
        FakeAsyncClient.calls = 0
        client = LLMClient(
            LLMSettings(
                provider="gemini",
                model="gemini-3.5-flash-lite",
                max_retries=3,
                retry_base_seconds=0.01,
                timeout_seconds=5,
            )
        )
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-not-real"}):
            with patch("shared.llm.httpx.AsyncClient", FakeAsyncClient):
                with self.assertRaises(LLMError) as ctx:
                    asyncio.run(client.generate(system="s", user="u"))
        self.assertTrue(ctx.exception.retryable)
        self.assertEqual(FakeAsyncClient.calls, 3)
        self.assertNotIn("test-key-not-real", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
