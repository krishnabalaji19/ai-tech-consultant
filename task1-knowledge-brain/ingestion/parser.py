"""Turn messy HTML into a clean article JSON. No AI."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

NOISE_SELECTORS = [
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "noscript",
    ".the-article-link",
    ".article-vote",
    ".breadcrumb",
    "#related_articles",
    "#related-article-list",
    "#article_thumbs_up",
    "#article_thumbs_down",
]


@dataclass
class ImageRef:
    url: str
    alt: str
    nearby_text: str


@dataclass
class Section:
    heading: str
    text: str
    images: list[ImageRef] = field(default_factory=list)


@dataclass
class ParsedPage:
    url: str
    title: str
    page_type: str
    headings: list[str]
    text: str
    images: list[ImageRef]
    sections: list[Section]
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _page_title(soup: BeautifulSoup, body: Tag | None) -> str:
    if body:
        heading = body.select_one("h1.post-title, h1")
        if heading:
            title = _clean_space(heading.get_text(" ", strip=True))
            if title:
                return title
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return _clean_space(str(og["content"]).split("|")[0])
    if soup.title and soup.title.string:
        return _clean_space(soup.title.string.split("|")[0])
    return "Untitled"


def _strip_noise(root: Tag) -> None:
    for selector in NOISE_SELECTORS:
        for node in root.select(selector):
            node.decompose()


def _nearby_text(img: Tag, limit: int = 220) -> str:
    bits: list[str] = []
    prev = img.find_previous(["p", "li", "h2", "h3", "h4", "h5"])
    nxt = img.find_next(["p", "li", "h2", "h3", "h4", "h5"])
    if prev:
        bits.append(_clean_space(prev.get_text(" ", strip=True)))
    if nxt:
        bits.append(_clean_space(nxt.get_text(" ", strip=True)))
    return _clean_space(" ".join(bits))[:limit]


def _image_from_tag(img: Tag, page_url: str) -> ImageRef | None:
    src = img.get("src") or img.get("data-src")
    if not src or str(src).startswith("data:"):
        return None
    src = urljoin(page_url, str(src))
    alt = _clean_space(str(img.get("alt") or ""))
    return ImageRef(url=src, alt=alt, nearby_text=_nearby_text(img))


def _is_index_page(url: str, body: Tag | None, soup: BeautifulSoup, text: str) -> bool:
    if "/solutions/articles/" in url and body is not None and len(text) >= 80:
        return False
    if body is None:
        return True
    if len(text) < 80:
        return True
    listing_links = soup.select(".article-list a, .list-lead a")
    if listing_links and "/solutions/articles/" not in url:
        return True
    return False


def _inside(el: Tag, names: set[str]) -> bool:
    return el.find_parent(list(names)) is not None


def _list_text(el: Tag) -> str:
    items: list[str] = []
    for i, li in enumerate(el.find_all("li", recursive=False), start=1):
        item = _clean_space(li.get_text(" ", strip=True))
        if item:
            prefix = f"{i}." if el.name == "ol" else "-"
            items.append(f"{prefix} {item}")
    return "\n".join(items)


def _table_text(table: Tag) -> str:
    rows: list[str] = []
    for tr in table.find_all("tr"):
        cells = [
            _clean_space(cell.get_text(" ", strip=True))
            for cell in tr.find_all(["th", "td"])
        ]
        line = " | ".join(cell for cell in cells if cell)
        if line:
            rows.append(line)
    return "\n".join(rows)


def _section_blocks(body: Tag, page_url: str) -> list[Section]:
    """Walk headings, lists, tables, and images in page order, even if nested in divs."""
    sections: list[Section] = []
    heading = "Introduction"
    texts: list[str] = []
    images: list[ImageRef] = []

    def flush() -> None:
        nonlocal heading, texts, images
        text = "\n".join(t for t in texts if t)
        if text or images:
            sections.append(Section(heading=heading, text=text, images=list(images)))
        texts = []
        images = []

    for el in body.find_all(["h1", "h2", "h3", "h4", "h5", "p", "ul", "ol", "table", "img"]):
        if el.name == "h1":
            continue
        if el.name in {"h2", "h3", "h4", "h5"}:
            flush()
            heading = _clean_space(el.get_text(" ", strip=True)) or heading
            continue
        if el.name == "img":
            ref = _image_from_tag(el, page_url)
            if ref:
                images.append(ref)
            continue
        if _inside(el, {"li", "td", "th"}):
            continue
        if el.name in {"ul", "ol"}:
            if _inside(el, {"ul", "ol"}):
                continue
            piece = _list_text(el)
            if piece:
                texts.append(piece)
            continue
        if el.name == "table":
            if _inside(el, {"table"}):
                continue
            piece = _table_text(el)
            if piece:
                texts.append(piece)
            continue
        piece = _clean_space(el.get_text(" ", strip=True))
        if piece:
            texts.append(piece)

    flush()
    return [s for s in sections if s.text or s.images]


def parse_html(html: str, url: str, content_hash: str | None = None) -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")
    body = (
        soup.select_one("#article-body")
        or soup.select_one(".article-body")
        or soup.select_one("article")
    )
    if body:
        _strip_noise(body)
        title = _page_title(soup, body)
        sections = _section_blocks(body, url)
        headings = [s.heading for s in sections if s.heading and s.heading != "Introduction"]
        text = "\n\n".join(s.text for s in sections if s.text)
        images = [img for s in sections for img in s.images]
    else:
        title = _page_title(soup, None)
        sections = []
        headings = []
        text = ""
        images = []

    page_type = "index" if _is_index_page(url, body, soup, text) else "article"
    if page_type == "index":
        sections = []
        images = []
        headings = []
        text = text if "/solutions/articles/" in url else ""

    return ParsedPage(
        url=url,
        title=title,
        page_type=page_type,
        headings=headings,
        text=text,
        images=images,
        sections=sections,
        content_hash=content_hash,
    )
