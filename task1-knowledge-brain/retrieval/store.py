"""On-disk Chroma store with stable chunk IDs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb

from ingestion.config import CHROMA_DIR, CHROMA_COLLECTION


@dataclass
class SearchHit:
    text: str
    url: str
    title: str
    section_heading: str
    distance: float
    image_urls: str


class ChromaStore:
    def __init__(self, persist_dir: Path | None = None, collection_name: str | None = None) -> None:
        self.persist_dir = persist_dir or CHROMA_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=collection_name or CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        if not ids:
            return
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def delete_ids(self, ids: list[str]) -> None:
        if not ids:
            return
        self.collection.delete(ids=ids)

    def count(self) -> int:
        return self.collection.count()

    def query(self, embedding: list[float], k: int = 3) -> list[SearchHit]:
        if self.count() == 0:
            return []
        k = min(k, self.count())
        raw = self.collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        hits: list[SearchHit] = []
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists, strict=False):
            meta = meta or {}
            hits.append(
                SearchHit(
                    text=doc or "",
                    url=str(meta.get("url", "")),
                    title=str(meta.get("title", "")),
                    section_heading=str(meta.get("section_heading", "")),
                    distance=float(dist),
                    image_urls=str(meta.get("image_urls", "")),
                )
            )
        return hits
