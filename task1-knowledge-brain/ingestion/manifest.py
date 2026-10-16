"""Save crawl progress so a stop halfway can resume later."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class PageRecord:
    url: str
    status: str
    attempts: int = 0
    last_modified: str | None = None
    content_hash: str | None = None
    http_status: int | None = None
    html_path: str | None = None
    fetched_at: str | None = None
    error: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_manifest(sitemap_url: str) -> dict[str, Any]:
    return {
        "version": 1,
        "source_sitemap": sitemap_url,
        "updated_at": now_iso(),
        "pages": {},
    }


def load_manifest(path: Path, sitemap_url: str) -> dict[str, Any]:
    if not path.exists():
        return empty_manifest(sitemap_url)
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("pages", {})
    data["source_sitemap"] = sitemap_url
    return data


def record_from_dict(url: str, raw: dict[str, Any]) -> PageRecord:
    return PageRecord(
        url=raw.get("url", url),
        status=str(raw.get("status", "pending")),
        attempts=int(raw.get("attempts", 0)),
        last_modified=raw.get("last_modified"),
        content_hash=raw.get("content_hash"),
        http_status=raw.get("http_status"),
        html_path=raw.get("html_path"),
        fetched_at=raw.get("fetched_at"),
        error=raw.get("error"),
    )


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest["updated_at"] = now_iso()
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def upsert_page(manifest: dict[str, Any], record: PageRecord) -> None:
    manifest["pages"][record.url] = asdict(record)


def should_skip_unchanged(record: PageRecord | None, sitemap_last_modified: str | None) -> bool:
    """Skip a new download when we already have HTML and the sitemap date matches."""
    if record is None:
        return False
    if record.status not in {"fetched", "skipped_unchanged"}:
        return False
    if not record.html_path or not record.content_hash:
        return False
    if sitemap_last_modified and record.last_modified:
        return sitemap_last_modified == record.last_modified
    # No lastmod on sitemap: skip only if we already stored a successful file.
    return record.status == "fetched" and sitemap_last_modified is None
