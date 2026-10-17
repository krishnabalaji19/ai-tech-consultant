"""Search the on-disk Chroma index. Usage: python3 -m retrieval.search "question"."""

from __future__ import annotations

import sys

from retrieval.embedder import MiniLMEmbedder
from retrieval.store import ChromaStore


def search(query: str, k: int = 3) -> list[dict[str, str | float]]:
    embedder = MiniLMEmbedder()
    store = ChromaStore()
    vector = embedder.encode([query])[0]
    hits = store.query(vector, k=k)
    return [
        {
            "title": hit.title,
            "url": hit.url,
            "section_heading": hit.section_heading,
            "text": hit.text,
            "distance": hit.distance,
        }
        for hit in hits
    ]


def main() -> None:
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        print('Usage: python3 -m retrieval.search "how do I refund a payment"')
        raise SystemExit(2)
    hits = search(query, k=3)
    if not hits:
        print("No chunks in the index. Run: make crawl && make ingest")
        return
    print(f'Top {len(hits)} chunks for: {query}\n')
    for i, hit in enumerate(hits, start=1):
        print(f"{i}. {hit['title']}")
        print(f"   URL: {hit['url']}")
        print(f"   Section: {hit['section_heading']}")
        preview = str(hit["text"]).replace("\n", " ")
        if len(preview) > 280:
            preview = preview[:280] + "..."
        print(f"   {preview}\n")


if __name__ == "__main__":
    main()
