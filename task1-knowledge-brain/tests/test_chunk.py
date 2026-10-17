"""Chunking tests. No embeddings and no AI."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

TASK1_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK1_ROOT))

from ingestion.parser import parse_html
from retrieval.chunk import chunk_page, stable_chunk_id

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ChunkTests(unittest.TestCase):
    def test_index_pages_are_not_chunked(self) -> None:
        html = (FIXTURES / "index.html").read_text(encoding="utf-8")
        page = parse_html(html, "https://example.com/support/solutions/1")
        self.assertEqual(chunk_page(page), [])

    def test_chunks_keep_title_url_heading_and_lists(self) -> None:
        html = (FIXTURES / "article.html").read_text(encoding="utf-8")
        url = "https://example.com/support/solutions/articles/1-refunds"
        page = parse_html(html, url)
        chunks = chunk_page(page)
        self.assertGreaterEqual(len(chunks), 2)
        refund_chunk = next(
            chunk for chunk in chunks if "How to Process a Refund?" in chunk.section_heading
        )
        self.assertEqual(refund_chunk.title, "How Refunds work")
        self.assertEqual(refund_chunk.url, url)
        self.assertIn("1. Open Billing.", refund_chunk.text)
        self.assertIn("2. Select the paid order.", refund_chunk.text)
        self.assertTrue(any(img.alt for img in refund_chunk.images))

    def test_chunk_ids_are_stable(self) -> None:
        html = (FIXTURES / "article.html").read_text(encoding="utf-8")
        url = "https://example.com/support/solutions/articles/1-refunds"
        first = chunk_page(parse_html(html, url))
        second = chunk_page(parse_html(html, url))
        self.assertEqual([c.chunk_id for c in first], [c.chunk_id for c in second])
        self.assertEqual(
            first[0].chunk_id,
            stable_chunk_id(url, first[0].section_heading, first[0].chunk_index),
        )


if __name__ == "__main__":
    unittest.main()
