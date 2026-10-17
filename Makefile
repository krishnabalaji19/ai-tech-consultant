# Stage 3: crawl, ingest, search, Knowledge Brain API.

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
TASK1_HOST ?= 127.0.0.1
TASK1_PORT ?= 8001

.PHONY: help venv test crawl ingest search api run

help:
	@echo "AI Tech Consultant"
	@echo "  make venv     — create .venv and install Python packages"
	@echo "  make test     — unit tests (no website, no paid APIs)"
	@echo "  make crawl    — download up to INGEST_MAX_PAGES help articles"
	@echo "  make ingest   — parse, chunk, embed locally, store in Chroma"
	@echo "  make search   — example search query (prints distance/score)"
	@echo "  make api      — start the Knowledge Brain at http://$(TASK1_HOST):$(TASK1_PORT)"
	@echo "  make run      — start all three services (not implemented yet)"

venv:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

test:
	cd task1-knowledge-brain && PYTHONPATH=..:$$PWD ../$(PYTHON) -m unittest discover -s tests -v

crawl-test: test

crawl:
	cd task1-knowledge-brain && ../$(PYTHON) -m ingestion

ingest:
	cd task1-knowledge-brain && ../$(PYTHON) -m retrieval.ingest

search:
	cd task1-knowledge-brain && ../$(PYTHON) -m retrieval.search "how do I refund a payment"

api:
	cd task1-knowledge-brain && PYTHONPATH=..:$$PWD ../$(PYTHON) -m uvicorn app.main:app --host $(TASK1_HOST) --port $(TASK1_PORT)

run:
	@echo "Full stack is not wired yet. For Stage 3 use: make api"
