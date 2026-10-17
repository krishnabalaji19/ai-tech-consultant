"""SQLite for answer cache, escalations, and reviewed expert records."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def question_key(question: str) -> str:
    normalized = " ".join(question.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class KnowledgeDB:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init()

    def _init(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS query_cache (
                question_key TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS escalations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                evidence TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                version INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS expert_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                escalation_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                version INTEGER NOT NULL,
                reviewed INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (escalation_id) REFERENCES escalations(id)
            );
            """
        )
        self.conn.commit()

    def get_cached(self, question: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT response_json FROM query_cache WHERE question_key = ?",
            (question_key(question),),
        ).fetchone()
        if not row:
            return None
        import json

        return json.loads(row["response_json"])

    def put_cached(self, question: str, response: dict[str, Any]) -> None:
        import json

        self.conn.execute(
            """
            INSERT OR REPLACE INTO query_cache(question_key, question, response_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (question_key(question), question, json.dumps(response), _now()),
        )
        self.conn.commit()

    def create_escalation(self, question: str, evidence: str, reason: str) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO escalations(question, evidence, reason, status, created_at, version)
            VALUES (?, ?, ?, 'open', ?, 0)
            """,
            (question, evidence, reason, _now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_open(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id, question, evidence, reason, status, created_at, resolved_at, version
            FROM escalations
            WHERE status = 'open'
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def get_escalation(self, escalation_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT id, question, evidence, reason, status, created_at, resolved_at, version
            FROM escalations WHERE id = ?
            """,
            (escalation_id,),
        ).fetchone()
        return dict(row) if row else None

    def resolve_escalation(self, escalation_id: int, answer: str) -> dict[str, Any]:
        existing = self.get_escalation(escalation_id)
        if existing is None:
            raise KeyError(escalation_id)
        version = int(existing["version"]) + 1
        now = _now()
        self.conn.execute(
            """
            UPDATE escalations
            SET status = 'resolved', resolved_at = ?, version = ?
            WHERE id = ?
            """,
            (now, version, escalation_id),
        )
        self.conn.execute(
            """
            INSERT INTO expert_records(
                escalation_id, question, answer, version, reviewed, created_at
            ) VALUES (?, ?, ?, ?, 1, ?)
            """,
            (escalation_id, existing["question"], answer, version, now),
        )
        self.conn.commit()
        record = self.get_escalation(escalation_id)
        assert record is not None
        record["answer"] = answer
        record["reviewed"] = True
        return record
