# Stage 1: polite crawl. Later stages will add `make run`.

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip

.PHONY: help venv crawl crawl-test run

help:
	@echo "AI Tech Consultant"
	@echo "  make venv        — create .venv and install Python packages"
	@echo "  make crawl-test  — unit tests (no website calls)"
	@echo "  make crawl       — download up to INGEST_MAX_PAGES help pages"
	@echo "  make run         — start all three services (not implemented yet)"

venv:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

crawl-test:
	cd task1-knowledge-brain && ../$(PYTHON) -m unittest discover -s tests -v

crawl:
	cd task1-knowledge-brain && ../$(PYTHON) -m ingestion

run:
	@echo "Services are not wired yet. For Stage 1 use: make crawl"
