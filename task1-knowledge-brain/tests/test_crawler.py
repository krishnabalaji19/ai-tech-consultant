"""Checks for retry rules and skip-unchanged logic. No live website calls."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

TASK1_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK1_ROOT))

from ingestion.crawler import is_retryable_http_status
from ingestion.manifest import PageRecord, should_skip_unchanged
from ingestion.sitemap import parse_sitemap_xml


class RetryTests(unittest.TestCase):
    def test_retries_temporary_status_codes(self) -> None:
        for code in (408, 429, 500, 502, 503, 504):
            self.assertTrue(is_retryable_http_status(code), msg=str(code))

    def test_does_not_retry_permanent_status_codes(self) -> None:
        for code in (400, 401, 403, 404, 410):
            self.assertFalse(is_retryable_http_status(code), msg=str(code))


class SkipUnchangedTests(unittest.TestCase):
    def test_skips_when_lastmod_matches_and_html_exists(self) -> None:
        record = PageRecord(
            url="https://example.com/a",
            status="fetched",
            last_modified="2026-10-11T08:00:54+00:00",
            content_hash="abc",
            html_path="raw_html/abc.html",
        )
        self.assertTrue(
            should_skip_unchanged(record, "2026-10-11T08:00:54+00:00")
        )

    def test_refetches_when_lastmod_changes(self) -> None:
        record = PageRecord(
            url="https://example.com/a",
            status="fetched",
            last_modified="2026-01-01T00:00:00+00:00",
            content_hash="abc",
            html_path="raw_html/abc.html",
        )
        self.assertFalse(
            should_skip_unchanged(record, "2026-10-11T08:00:54+00:00")
        )

    def test_refetches_failed_pages(self) -> None:
        record = PageRecord(
            url="https://example.com/a",
            status="failed_temporary",
            last_modified="2026-10-11T08:00:54+00:00",
            content_hash=None,
            html_path=None,
        )
        self.assertFalse(
            should_skip_unchanged(record, "2026-10-11T08:00:54+00:00")
        )


class SitemapParseTests(unittest.TestCase):
    def test_parses_loc_and_lastmod(self) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url>
            <loc>https://example.com/one</loc>
            <lastmod>2026-10-11T08:00:54+00:00</lastmod>
          </url>
          <url>
            <loc>https://example.com/one</loc>
          </url>
          <url>
            <loc>https://example.com/two</loc>
          </url>
        </urlset>
        """
        entries = parse_sitemap_xml(xml)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].url, "https://example.com/one")
        self.assertEqual(entries[0].last_modified, "2026-10-11T08:00:54+00:00")
        self.assertEqual(entries[1].url, "https://example.com/two")


if __name__ == "__main__":
    unittest.main()
