"""HTTP tests for the Knowledge Brain. Fake LLM, no Gemini."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TASK1_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TASK1_ROOT.parent
sys.path.insert(0, str(TASK1_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from app.db import KnowledgeDB
from app.main import create_app
from app.query import QueryService
from retrieval.store import SearchHit
from test_query import FakeEmbedder, FakeLLM, FakeRetriever, FakeStore, _hit


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.llm = FakeLLM()
        self.store = FakeStore()
        service = QueryService(
            db=KnowledgeDB(Path(self.tmp.name) / "api.db"),
            retriever=FakeRetriever([_hit(0.2)]),
            llm=self.llm,
            store=self.store,
            embedder=FakeEmbedder(),
            prompt_loader=lambda: "prompt",
            top_k=5,
            max_distance=0.85,
        )
        self.client = TestClient(create_app(service=service))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertNotIn("api_key", str(body).lower())
        self.assertNotIn("GEMINI_API_KEY", str(body))

    def test_query_and_chat_page(self) -> None:
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Knowledge Brain", page.text)
        asked = self.client.post("/query", json={"question": "How do I refund a payment?"})
        self.assertEqual(asked.status_code, 200)
        body = asked.json()
        self.assertEqual(body["status"], "answered")
        self.assertEqual(self.llm.calls, 1)

    def test_escalation_list_and_resolve(self) -> None:
        created = self.client.post(
            "/escalations",
            json={"question": "Need a human", "evidence": "none", "reason": "manual"},
        )
        self.assertEqual(created.status_code, 200)
        escalation_id = created.json()["id"]
        opened = self.client.get("/escalations")
        self.assertEqual(len(opened.json()), 1)
        resolved = self.client.post(
            f"/escalations/{escalation_id}/resolve",
            json={"answer": "Here is the expert answer."},
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["status"], "resolved")
        self.assertEqual(self.client.get("/escalations").json(), [])
        self.assertEqual(len(self.store.ids), 1)


if __name__ == "__main__":
    unittest.main()
