# Task 1 — Knowledge Brain

Reads Brilliant Directories help articles, stores them, and answers questions with source URLs.

**This folder in simple words**

- `app/` — the website/API people (and Tasks 2 and 3) call.
- `ingestion/` — download pages politely and remember progress.
- `retrieval/` — split text, turn it into numbers, search similar pieces.
- `evaluation/` — real test questions and CSV results.
- `templates/` — a simple chat page.
- `tests/` — automated checks.

Stage 2: `make crawl` then `make ingest` from the repo root. Search with `python3 -m retrieval.search "how do I refund a payment"` from this folder (using the repo `.venv`).

The crawler prefers `/solutions/articles/` URLs so the 30-page cap is real articles, not category listings.
