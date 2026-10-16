"""Polite, resumable crawler. No AI calls."""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import Counter
from pathlib import Path

import httpx

from .config import DATA_DIR, MANIFEST_PATH, RAW_HTML_DIR, CrawlSettings, load_settings
from .manifest import (
    PageRecord,
    load_manifest,
    now_iso,
    record_from_dict,
    save_manifest,
    should_skip_unchanged,
    upsert_page,
)
from .robots import is_allowed, load_robots
from .sitemap import SitemapEntry, fetch_sitemap

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


def is_retryable_http_status(status_code: int) -> bool:
    return status_code in RETRYABLE_STATUS


def html_filename_for(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"{digest}.html"


def content_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


class RequestGate:
    """At most N downloads at once, and a pause between starting each one."""

    def __init__(self, max_concurrency: int, delay_seconds: float) -> None:
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self._delay = max(0.0, delay_seconds)
        self._lock = asyncio.Lock()
        self._next_start = 0.0

    async def acquire(self) -> None:
        await self._semaphore.acquire()
        async with self._lock:
            wait_for = self._next_start - time.monotonic()
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._next_start = time.monotonic() + self._delay

    def release(self) -> None:
        self._semaphore.release()


async def fetch_with_retries(
    client: httpx.AsyncClient,
    url: str,
    settings: CrawlSettings,
) -> httpx.Response:
    last_error: Exception | None = None
    attempts = max(1, settings.max_retries)
    for attempt in range(attempts):
        try:
            response = await client.get(url)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(settings.retry_base_seconds * (2**attempt))
            continue

        if is_retryable_http_status(response.status_code):
            if attempt == attempts - 1:
                return response
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                delay = float(retry_after)
            else:
                delay = settings.retry_base_seconds * (2**attempt)
            await asyncio.sleep(delay)
            continue

        return response

    if last_error:
        raise last_error
    raise RuntimeError(f"No response for {url}")


def _relative_html_path(url: str) -> str:
    return str(Path("raw_html") / html_filename_for(url))


async def crawl_one_page(
    *,
    client: httpx.AsyncClient,
    gate: RequestGate,
    settings: CrawlSettings,
    entry: SitemapEntry,
    previous: PageRecord | None,
    manifest: dict,
    manifest_lock: asyncio.Lock,
) -> str:
    if should_skip_unchanged(previous, entry.last_modified):
        skipped = PageRecord(
            url=entry.url,
            status="skipped_unchanged",
            attempts=previous.attempts if previous else 0,
            last_modified=entry.last_modified,
            content_hash=previous.content_hash if previous else None,
            http_status=previous.http_status if previous else None,
            html_path=previous.html_path if previous else None,
            fetched_at=previous.fetched_at if previous else None,
            error=None,
        )
        async with manifest_lock:
            upsert_page(manifest, skipped)
            save_manifest(MANIFEST_PATH, manifest)
        return skipped.status

    await gate.acquire()
    try:
        attempts_used = (previous.attempts if previous else 0) + 1
        try:
            response = await fetch_with_retries(client, entry.url, settings)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            failed = PageRecord(
                url=entry.url,
                status="failed_temporary",
                attempts=attempts_used,
                last_modified=entry.last_modified,
                content_hash=previous.content_hash if previous else None,
                html_path=previous.html_path if previous else None,
                error=str(exc),
            )
            async with manifest_lock:
                upsert_page(manifest, failed)
                save_manifest(MANIFEST_PATH, manifest)
            return failed.status

        if response.status_code >= 400:
            status = (
                "failed_temporary"
                if is_retryable_http_status(response.status_code)
                else "failed_permanent"
            )
            failed = PageRecord(
                url=entry.url,
                status=status,
                attempts=attempts_used,
                last_modified=entry.last_modified,
                http_status=response.status_code,
                content_hash=previous.content_hash if previous else None,
                html_path=previous.html_path if previous else None,
                error=f"HTTP {response.status_code}",
            )
            async with manifest_lock:
                upsert_page(manifest, failed)
                save_manifest(MANIFEST_PATH, manifest)
            return failed.status

        body = response.content
        digest = content_hash(body)
        rel_path = _relative_html_path(entry.url)
        dest = DATA_DIR / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)

        if (
            previous
            and previous.content_hash == digest
            and previous.status in {"fetched", "skipped_unchanged"}
        ):
            page_status = "skipped_unchanged"
        else:
            page_status = "fetched"

        record = PageRecord(
            url=entry.url,
            status=page_status,
            attempts=attempts_used,
            last_modified=entry.last_modified,
            content_hash=digest,
            http_status=response.status_code,
            html_path=rel_path,
            fetched_at=now_iso(),
            error=None,
        )
        async with manifest_lock:
            upsert_page(manifest, record)
            save_manifest(MANIFEST_PATH, manifest)
        return record.status
    finally:
        gate.release()


async def run_crawl(settings: CrawlSettings | None = None) -> dict[str, int]:
    settings = settings or load_settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)

    timeout = httpx.Timeout(settings.timeout_seconds)
    headers = {"User-Agent": settings.user_agent, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8"}

    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        robots = await load_robots(client, settings.robots_url, settings.user_agent)
        if not is_allowed(robots, settings.user_agent, settings.sitemap_url):
            raise PermissionError(f"robots.txt disallows the sitemap: {settings.sitemap_url}")

        entries = await fetch_sitemap(client, settings.sitemap_url)
        manifest = load_manifest(MANIFEST_PATH, settings.sitemap_url)
        manifest_lock = asyncio.Lock()
        chosen: list[SitemapEntry] = []
        statuses: list[str] = []

        async with manifest_lock:
            for entry in entries:
                if not is_allowed(robots, settings.user_agent, entry.url):
                    upsert_page(
                        manifest,
                        PageRecord(
                            url=entry.url,
                            status="skipped_robots",
                            last_modified=entry.last_modified,
                            error="Disallowed by robots.txt",
                        ),
                    )
                    statuses.append("skipped_robots")
                    continue
                chosen.append(entry)
                existing_raw = manifest["pages"].get(entry.url)
                if existing_raw is None:
                    upsert_page(
                        manifest,
                        PageRecord(
                            url=entry.url,
                            status="pending",
                            last_modified=entry.last_modified,
                        ),
                    )
                if len(chosen) >= settings.max_pages:
                    break
            save_manifest(MANIFEST_PATH, manifest)

        gate = RequestGate(settings.max_concurrency, settings.delay_seconds)

        async def worker(entry: SitemapEntry) -> str:
            previous_raw = manifest["pages"].get(entry.url)
            previous = record_from_dict(entry.url, previous_raw) if previous_raw else None
            try:
                return await crawl_one_page(
                    client=client,
                    gate=gate,
                    settings=settings,
                    entry=entry,
                    previous=previous,
                    manifest=manifest,
                    manifest_lock=manifest_lock,
                )
            except Exception as exc:  # one page must not stop the crawl
                failed = PageRecord(
                    url=entry.url,
                    status="failed_temporary",
                    attempts=(previous.attempts if previous else 0) + 1,
                    last_modified=entry.last_modified,
                    error=str(exc),
                )
                async with manifest_lock:
                    upsert_page(manifest, failed)
                    save_manifest(MANIFEST_PATH, manifest)
                return failed.status

        results = await asyncio.gather(*(worker(entry) for entry in chosen))
        statuses.extend(results)

    counts = dict(Counter(statuses))
    counts["selected_pages"] = len(chosen)
    return counts
