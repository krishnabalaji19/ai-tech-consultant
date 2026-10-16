# AI Tech Consultant

Helps a software business answer product questions, draft customer emails, and turn meeting notes into a scope of work.

Three Python apps share one Knowledge Brain over HTTP:

1. **Task 1 Knowledge Brain** — reads help articles and answers with source URLs.
2. **Task 2 Inbox Agent** — classifies emails and drafts replies for human approval.
3. **Task 3 Meeting to Scope** — turns transcripts into requirements, estimates, and a proposal.

## Status

Stage 1: polite crawler (no AI). Saves HTML and a resume manifest under `data/`.

## Setup

1. Copy `.env.example` to `.env` if needed (you already have `.env`).
2. `make venv` then `make crawl-test` then `make crawl`.
3. `make run` for all three services is not implemented yet.

## Honest limits (planned)

- First crawl is about 30 pages, not the full sitemap.
- Screenshot understanding is simplified.
- Default model is Gemini free tier. Claude is a config switch; we will not pay to benchmark it.
