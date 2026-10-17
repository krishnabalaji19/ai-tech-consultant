"""Re-ingest planning tests. No Chroma download and no AI."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

TASK1_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK1_ROOT))

from ingestion.config import CrawlSettings
from ingestion.crawler import mark_unselected_removed, select_crawl_targets
from ingestion.manifest import PageRecord, empty_manifest, upsert_page
from ingestion.sitemap import SitemapEntry
from retrieval.ingest import plan_ingest


class IngestPlanTests(unittest.TestCase):
    def test_skips_unchanged_hash_and_deletes_removed_urls(self) -> None:
        current = {
            "https://a.example/keep": {
                "url": "https://a.example/keep",
                "content_hash": "aaa",
                "html_path": "raw_html/keep.html",
            },
            "https://a.example/changed": {
                "url": "https://a.example/changed",
                "content_hash": "new",
                "html_path": "raw_html/changed.html",
            },
        }
        previous = {
            "pages": {
                "https://a.example/keep": {
                    "content_hash": "aaa",
                    "chunk_ids": ["keep-1"],
                },
                "https://a.example/changed": {
                    "content_hash": "old",
                    "chunk_ids": ["old-1"],
                },
                "https://a.example/gone": {
                    "content_hash": "zzz",
                    "chunk_ids": ["gone-1"],
                },
            }
        }
        plan = plan_ingest(current, previous)
        self.assertEqual(plan.unchanged, ["https://a.example/keep"])
        self.assertEqual(plan.to_process, ["https://a.example/changed"])
        self.assertEqual(plan.to_delete, ["https://a.example/gone"])


class SelectTargetsTests(unittest.TestCase):
    def test_prefers_article_urls_and_refund_priority(self) -> None:
        entries = [
            SitemapEntry("https://x.example/support/home", None),
            SitemapEntry("https://x.example/support/solutions/1", None),
            SitemapEntry("https://x.example/support/solutions/articles/2-email", None),
            SitemapEntry("https://x.example/support/solutions/articles/3-how-refunds-work", None),
        ]
        settings = CrawlSettings(
            sitemap_url="https://x.example/sitemap.xml",
            robots_url="https://x.example/robots.txt",
            user_agent="test",
            max_pages=2,
            max_concurrency=2,
            delay_seconds=0,
            max_retries=1,
            retry_base_seconds=0,
            timeout_seconds=5,
            path_contains="/solutions/articles/",
            priority_substrings=("refund",),
        )
        chosen, blocked = select_crawl_targets(
            entries,
            is_url_allowed=lambda url: "login" not in url,
            settings=settings,
        )
        self.assertEqual(blocked, [])
        urls = [item.url for item in chosen]
        self.assertEqual(len(urls), 2)
        self.assertIn(
            "https://x.example/support/solutions/articles/3-how-refunds-work",
            urls,
        )
        self.assertTrue(all("/solutions/articles/" in url for url in urls))


class RemovedPagesTests(unittest.TestCase):
    def test_drops_old_urls_and_deletes_html(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            html = data_dir / "raw_html"
            html.mkdir()
            stale = html / "old.html"
            stale.write_text("gone", encoding="utf-8")
            manifest = empty_manifest("https://example.com/sitemap.xml")
            upsert_page(
                manifest,
                PageRecord(
                    url="https://example.com/old",
                    status="fetched",
                    html_path="raw_html/old.html",
                    content_hash="abc",
                ),
            )
            upsert_page(
                manifest,
                PageRecord(
                    url="https://example.com/keep",
                    status="fetched",
                    html_path="raw_html/keep.html",
                    content_hash="def",
                ),
            )
            removed = mark_unselected_removed(
                manifest,
                {"https://example.com/keep"},
                data_dir,
            )
            self.assertEqual(removed, 1)
            self.assertEqual(manifest["pages"]["https://example.com/old"]["status"], "removed")
            self.assertFalse(stale.exists())
            self.assertEqual(manifest["pages"]["https://example.com/keep"]["status"], "fetched")


if __name__ == "__main__":
    unittest.main()
