# AI Tech Consultant (partial submission)

Capstone for Business Labs. **Only Task 1 (Knowledge Brain) was worked on.
Tasks 2 and 3 were not built.**

## What works (tested)
- Polite, resumable crawler for the Brilliant Directories sitemap
  (robots.txt respected, rate limit, retries, manifest, skips unchanged pages).
- Parser and chunker: title, headings, lists, image alt text kept per chunk.
- Local embeddings (MiniLM) stored in Chroma. 150 pages / 755 chunks indexed.
- Incremental re-ingest: unchanged pages skipped, removed pages deleted.
- Search script that returns the right article for "how do I refund a payment".
- Unit tests: [14 passing / update with your real result].

## Partly done / not verified
- [Query API with escalation: written with an AI coding tool, NOT fully
  tested by me. Update this line after you try it.]

## Not done
- Task 2 (Inbox Agent), Task 3 (Meeting to Scope).
- Real image understanding (only alt text and nearby text are used).
- Evaluations (20+ cases per task) and model comparison. No scores are
  claimed because none were run.
- Claude was not used, because I could not afford API costs.

## Known weakness (real example)
Searching "how do I change my logo" does not return a logo article. Vector
search always returns something, so a "too far away, say I don't know"
cutoff is needed.

## Run it
    make venv
    make test
    make crawl
    make ingest
    make search

Secrets live in `.env` (not committed). Copy `.env.example` to `.env`.

## Honest note on tools
I used Cursor for coding. Its free usage limit ran out, I used additional
free accounts, and then Cursor blocked free trials on my machine during
Stage 3. I also used Claude chat for planning and guidance.