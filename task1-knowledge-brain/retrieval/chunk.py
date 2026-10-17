"""Split an article into searchable pieces without breaking lists."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from ingestion.parser import ImageRef, ParsedPage

MAX_CHUNK_CHARS = 1200


@dataclass
class Chunk:
    chunk_id: str
    url: str
    title: str
    section_heading: str
    text: str
    images: list[ImageRef]
    chunk_index: int

    def to_metadata(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "section_heading": self.section_heading,
            "chunk_index": self.chunk_index,
            "image_urls": " | ".join(img.url for img in self.images),
            "image_alts": " | ".join(img.alt for img in self.images if img.alt),
        }

    def embed_text(self) -> str:
        image_notes = []
        for img in self.images:
            alt = img.alt or img.nearby_text
            if alt:
                image_notes.append(f"[image] {alt}")
        extra = "\n".join(image_notes)
        return f"{self.title}\n{self.section_heading}\n{self.text}\n{extra}".strip()


def stable_chunk_id(url: str, section_heading: str, chunk_index: int) -> str:
    raw = f"{url}|{section_heading}|{chunk_index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _split_paragraphs(text: str) -> list[str]:
    blocks = [b.strip() for b in re.split(r"\n{2,}", text) if b.strip()]
    return blocks or ([text.strip()] if text.strip() else [])


def _is_list_block(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    return all(ln.startswith(("- ", "* ")) or re.match(r"^\d+\.\s", ln) for ln in lines)


def _pack_blocks(heading: str, blocks: list[str], images: list[ImageRef]) -> list[tuple[str, list[ImageRef]]]:
    packed: list[tuple[str, list[ImageRef]]] = []
    buf: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal buf, size
        if buf:
            packed.append(("\n\n".join(buf), list(images) if not packed else []))
            buf = []
            size = 0

    for block in blocks:
        block_len = len(block)
        if _is_list_block(block):
            if buf and size + block_len > MAX_CHUNK_CHARS:
                flush()
            if buf and size + block_len <= MAX_CHUNK_CHARS:
                buf.append(block)
                size += block_len
            else:
                flush()
                packed.append((block, list(images) if not packed else []))
            continue
        if buf and size + block_len > MAX_CHUNK_CHARS:
            flush()
        buf.append(block)
        size += block_len
    flush()
    if packed:
        packed[0] = (packed[0][0], list(images))
    return packed


def chunk_page(page: ParsedPage) -> list[Chunk]:
    if page.page_type != "article":
        return []
    chunks: list[Chunk] = []
    index = 0
    for section in page.sections:
        blocks = _split_paragraphs(section.text)
        if not blocks and section.images:
            blocks = ["[images in this section]"]
        for text, images in _pack_blocks(section.heading, blocks, section.images):
            chunks.append(
                Chunk(
                    chunk_id=stable_chunk_id(page.url, section.heading, index),
                    url=page.url,
                    title=page.title,
                    section_heading=section.heading,
                    text=text,
                    images=images,
                    chunk_index=index,
                )
            )
            index += 1
    return chunks
