# Task 1 — Knowledge Brain

Reads Brilliant Directories help articles, stores them, and answers questions with source URLs.

**This folder in simple words**

- `app/` — the website/API people (and Tasks 2 and 3) call.
- `ingestion/` — download pages politely and remember progress.
- `retrieval/` — split text, turn it into numbers, search similar pieces.
- `evaluation/` — real test questions and CSV results.
- `templates/` — a simple chat page.
- `tests/` — automated checks.

Stage 1: run the crawler from the repo root with `make crawl`. HTML and `data/crawl_manifest.json` are written at the repo root, not inside this folder.
