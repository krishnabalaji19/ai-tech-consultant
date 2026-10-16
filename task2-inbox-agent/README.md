# Task 2 — Inbox Agent

Reads customer emails, asks Task 1 over HTTP (never imports Task 1 code), and drafts a reply you must approve.

**This folder in simple words**

- `app/` — the review screen and API.
- `email/` — classify the request type.
- `knowledge_client.py` (later) — talks to Task 1 like a separate product.
- `drafting/` — build a JSON draft the computer cannot “send” alone.
- `feedback/` — save your edits and count unchanged drafts per category.
- `data/` — the 50 practice emails.
- `templates/` — the inbox review page.
- `tests/` — automated checks.

Refunds, quotes, and complaints never auto-send.

Stage 0: empty placeholders only.
