# AI Tech Consultant

Helps a software business answer product questions, draft customer emails, and turn meeting notes into a scope of work.

Three Python apps share one Knowledge Brain over HTTP:

1. **Task 1 Knowledge Brain** — reads help articles and answers with source URLs.
2. **Task 2 Inbox Agent** — classifies emails and drafts replies for human approval.
3. **Task 3 Meeting to Scope** — turns transcripts into requirements, estimates, and a proposal.

## Status

Stage 3: Knowledge Brain API + chat page. Default LLM is `gemini-3.5-flash-lite` (free tier; `gemini-2.0-flash` is shut down).

## Setup

1. Copy `.env.example` to `.env` if needed (you already have `.env`).
2. `make venv`
3. `make test`
4. `make crawl` then `make ingest`
5. `make search` (prints distance and score)
6. `make api` then open http://127.0.0.1:8001/

## Honest limits (planned)

- First crawl is about 30 pages, not the full sitemap.
- Screenshot understanding is simplified.
- Default model is Gemini free tier. Claude is a config switch; we will not pay to benchmark it.
