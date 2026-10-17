# Stage 2: crawl, parse, embed, search. Later stages add `make run`.

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip

.PHONY: help venv test crawl ingest search run

help:
	@echo "AI Tech Consultant"
	@echo "  make venv     — create .venv and install Python packages"
	@echo "  make test     — unit tests (no website, no paid APIs)"
	@echo "  make crawl    — download up to INGEST_MAX_PAGES help articles"
	@echo "  make ingest   — parse, chunk, embed locally, store in Chroma"
	@echo "  make search   — example search query"
	@echo "  make run      — start all three services (not implemented yet)"

venv:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

test:
	cd task1-knowledge-brain && ../$(PYTHON) -m unittest discover -s tests -v

crawl-test: test

crawl:
	cd task1-knowledge-brain && ../$(PYTHON) -m ingestion

ingest:
	cd task1-knowledge-brain && ../$(PYTHON) -m retrieval.ingest

search:
	cd task1-knowledge-brain && ../$(PYTHON) -m retrieval.search "how do I refund a payment"

run:
	@echo "Services are not wired yet. For Stage 2 use: make crawl && make ingest"
