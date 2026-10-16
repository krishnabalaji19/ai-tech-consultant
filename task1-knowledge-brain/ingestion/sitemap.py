"""Download the sitemap and pull out unique page URLs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


@dataclass(frozen=True)
class SitemapEntry:
    url: str
    last_modified: str | None


def parse_sitemap_xml(xml_text: str) -> list[SitemapEntry]:
    """Turn sitemap XML into a de-duplicated list, keeping first-seen order."""
    root = ET.fromstring(xml_text)
    seen: set[str] = set()
    entries: list[SitemapEntry] = []

    for node in root.findall("sm:url", SITEMAP_NS):
        loc = node.findtext("sm:loc", default="", namespaces=SITEMAP_NS).strip()
        if not loc or loc in seen:
            continue
        lastmod = node.findtext("sm:lastmod", default=None, namespaces=SITEMAP_NS)
        if lastmod is not None:
            lastmod = lastmod.strip() or None
        seen.add(loc)
        entries.append(SitemapEntry(url=loc, last_modified=lastmod))

    if not entries:
        # Some sitemaps omit the default namespace.
        for node in root.findall("url"):
            loc_el = node.find("loc")
            loc = (loc_el.text or "").strip() if loc_el is not None else ""
            if not loc or loc in seen:
                continue
            lastmod_el = node.find("lastmod")
            lastmod = (
                (lastmod_el.text or "").strip() or None
                if lastmod_el is not None
                else None
            )
            seen.add(loc)
            entries.append(SitemapEntry(url=loc, last_modified=lastmod))

    return entries


async def fetch_sitemap(client: httpx.AsyncClient, sitemap_url: str) -> list[SitemapEntry]:
    response = await client.get(sitemap_url)
    response.raise_for_status()
    return parse_sitemap_xml(response.text)
