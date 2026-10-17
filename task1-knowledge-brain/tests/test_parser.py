"""Parser tests use local HTML fixtures. No website and no AI."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

TASK1_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK1_ROOT))

from ingestion.parser import parse_html

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ParserTests(unittest.TestCase):
    def test_article_extracts_title_text_headings_images(self) -> None:
        html = (FIXTURES / "article.html").read_text(encoding="utf-8")
        page = parse_html(
            html,
            "https://support.example.com/support/solutions/articles/1-how-refunds-work",
        )
        self.assertEqual(page.page_type, "article")
        self.assertEqual(page.title, "How Refunds work")
        self.assertNotIn("Login", page.text)
        self.assertNotIn("Copyright footer", page.text)
        self.assertNotIn("Unrelated extra", page.text)
        self.assertIn("Disclaimer", page.headings)
        self.assertIn("How to Process a Refund?", page.headings)
        self.assertIn("Some payment gateways do not permit refunds.", page.text)
        self.assertIn("Gateway | Refunds", page.text)
        self.assertIn("Stripe | Yes", page.text)
        alts = [img.alt for img in page.images]
        self.assertIn("Refund button in order details", alts)
        nearby = " ".join(img.nearby_text for img in page.images)
        self.assertIn("Open the order", nearby)

    def test_index_page_is_marked_and_has_no_sections(self) -> None:
        html = (FIXTURES / "index.html").read_text(encoding="utf-8")
        page = parse_html(
            html,
            "https://support.example.com/support/solutions/12000001358",
        )
        self.assertEqual(page.page_type, "index")
        self.assertEqual(page.sections, [])
        self.assertEqual(page.images, [])


if __name__ == "__main__":
    unittest.main()
