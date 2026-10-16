# AI Tech Consultant

Helps a software business answer product questions, draft customer emails, and turn meeting notes into a scope of work.

Three Python apps share one Knowledge Brain over HTTP:

1. **Task 1 Knowledge Brain** — reads help articles and answers with source URLs.
2. **Task 2 Inbox Agent** — classifies emails and drafts replies for human approval.
3. **Task 3 Meeting to Scope** — turns transcripts into requirements, estimates, and a proposal.

## Status

Stage 0: folder layout and git only. Nothing to run yet.

## Setup (after later stages)

1. Copy `.env.example` to `.env` (you already have `.env` with `GEMINI_API_KEY`).
2. Use Python 3. Create one virtual environment at the repo root when we add dependencies.
3. `make run` will start all three services (not implemented yet).

## Honest limits (planned)

- First crawl is about 30 pages, not the full sitemap.
- Screenshot understanding is simplified.
- Default model is Gemini free tier. Claude is a config switch; we will not pay to benchmark it.
