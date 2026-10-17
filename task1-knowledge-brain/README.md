# Task 1 — Knowledge Brain

Reads Brilliant Directories help articles, stores them, and answers questions with source URLs.

**This folder in simple words**

- `app/` — the website/API people (and Tasks 2 and 3) call.
- `ingestion/` — download pages politely and remember progress.
- `retrieval/` — split text, turn it into numbers, search similar pieces.
- `evaluation/` — real test questions and CSV results.
- `templates/` — a simple chat page.
- `tests/` — automated checks.

Stage 3: from the repo root run `make crawl`, `make ingest`, then `make api`. Open http://127.0.0.1:8001/ for the chat page. `POST /query` answers only from retrieved articles.

The crawler prefers `/solutions/articles/` URLs so the 30-page cap is real articles, not category listings.
