"""Parse crawled HTML, chunk articles, embed locally, write Chroma."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ingestion.config import (
    DATA_DIR,
    INGEST_MANIFEST_PATH,
    MANIFEST_PATH,
    PARSED_DIR,
)
from ingestion.crawler import html_filename_for
from ingestion.manifest import record_from_dict
from ingestion.parser import parse_html
from retrieval.chunk import Chunk, chunk_page
from retrieval.embedder import MiniLMEmbedder
from retrieval.store import ChromaStore


@dataclass
class IngestPlan:
    to_process: list[str]
    to_delete: list[str]
    unchanged: list[str]


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("pages", {})
    return data


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def current_crawled_pages(crawl_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for url, raw in crawl_manifest.get("pages", {}).items():
        record = record_from_dict(url, raw)
        if record.status not in {"fetched", "skipped_unchanged"}:
            continue
        if not record.html_path or not record.content_hash:
            continue
        current[url] = {
            "url": url,
            "content_hash": record.content_hash,
            "html_path": record.html_path,
        }
    return current


def plan_ingest(
    current: dict[str, dict[str, Any]],
    previous: dict[str, Any],
) -> IngestPlan:
    prev_pages = previous.get("pages", {})
    to_delete = [url for url in prev_pages if url not in current]
    to_process: list[str] = []
    unchanged: list[str] = []
    for url, page in current.items():
        prior = prev_pages.get(url)
        if (
            prior
            and prior.get("content_hash") == page["content_hash"]
            and "chunk_ids" in prior
        ):
            unchanged.append(url)
        else:
            to_process.append(url)
    return IngestPlan(to_process=to_process, to_delete=to_delete, unchanged=unchanged)


def parsed_path_for(url: str) -> Path:
    return PARSED_DIR / f"{Path(html_filename_for(url)).stem}.json"


class MemoryEmbedder:
    """Tiny stand-in used by tests. Not used in the real ingest command."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            seed = float(len(text) % 97) / 97.0
            vectors.append([seed, 1.0 - seed, 0.15])
        return vectors


def _upsert_chunks(store: ChromaStore, embedder: Any, chunks: list[Chunk]) -> list[str]:
    if not chunks:
        return []
    documents = [chunk.embed_text() for chunk in chunks]
    embeddings = embedder.encode(documents)
    store.upsert(
        ids=[chunk.chunk_id for chunk in chunks],
        documents=documents,
        metadatas=[chunk.to_metadata() for chunk in chunks],
        embeddings=embeddings,
    )
    return [chunk.chunk_id for chunk in chunks]


def run_ingest(
    *,
    store: ChromaStore | None = None,
    embedder: Any | None = None,
) -> dict[str, int]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    crawl = load_json(MANIFEST_PATH, {"pages": {}})
    ingest_manifest = load_json(INGEST_MANIFEST_PATH, {"pages": {}})
    current = current_crawled_pages(crawl)
    plan = plan_ingest(current, ingest_manifest)

    store = store or ChromaStore()
    if embedder is None:
        embedder = MiniLMEmbedder() if plan.to_process else MemoryEmbedder()

    deleted_vectors = 0
    for url in plan.to_delete:
        prior = ingest_manifest["pages"].get(url, {})
        ids = list(prior.get("chunk_ids") or [])
        store.delete_ids(ids)
        deleted_vectors += len(ids)
        parsed = Path(prior["parsed_path"]) if prior.get("parsed_path") else parsed_path_for(url)
        if parsed.exists():
            parsed.unlink()
        ingest_manifest["pages"].pop(url, None)

    processed = 0
    indexed_chunks = 0
    index_pages = 0
    for url in plan.to_process:
        page_info = current[url]
        html_file = DATA_DIR / page_info["html_path"]
        if not html_file.exists():
            continue
        html = html_file.read_text(encoding="utf-8", errors="replace")
        parsed = parse_html(html, url, content_hash=page_info["content_hash"])
        dest = parsed_path_for(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(parsed.to_dict(), indent=2), encoding="utf-8")

        prior_ids = list((ingest_manifest["pages"].get(url) or {}).get("chunk_ids") or [])
        store.delete_ids(prior_ids)

        chunks = chunk_page(parsed)
        chunk_ids = _upsert_chunks(store, embedder, chunks)
        ingest_manifest["pages"][url] = {
            "content_hash": page_info["content_hash"],
            "page_type": parsed.page_type,
            "parsed_path": str(dest.relative_to(DATA_DIR)),
            "chunk_ids": chunk_ids,
        }
        processed += 1
        indexed_chunks += len(chunk_ids)
        if parsed.page_type == "index":
            index_pages += 1

    save_json(INGEST_MANIFEST_PATH, ingest_manifest)
    return {
        "processed": processed,
        "unchanged": len(plan.unchanged),
        "deleted_pages": len(plan.to_delete),
        "deleted_vectors": deleted_vectors,
        "index_pages": index_pages,
        "chunks_upserted": indexed_chunks,
        "store_count": store.count(),
    }


def main() -> None:
    summary = run_ingest()
    print("Ingest finished (local MiniLM embeddings, no paid API).")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
