"""Run: from task1-knowledge-brain, `python3 -m ingestion`."""

from __future__ import annotations

import asyncio
import json

from .crawler import run_crawl


def main() -> None:
    summary = asyncio.run(run_crawl())
    print("Crawl finished (no AI was used).")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
