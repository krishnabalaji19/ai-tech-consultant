"""Read crawl settings from the repo-root .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

TASK1_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TASK1_ROOT.parent
DATA_DIR = REPO_ROOT / "data"
RAW_HTML_DIR = DATA_DIR / "raw_html"
PARSED_DIR = DATA_DIR / "parsed"
CHROMA_DIR = DATA_DIR / "chroma"
MANIFEST_PATH = DATA_DIR / "crawl_manifest.json"
INGEST_MANIFEST_PATH = DATA_DIR / "ingest_manifest.json"

load_dotenv(REPO_ROOT / ".env")

CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "help_chunks")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


@dataclass(frozen=True)
class CrawlSettings:
    sitemap_url: str
    robots_url: str
    user_agent: str
    max_pages: int
    max_concurrency: int
    delay_seconds: float
    max_retries: int
    retry_base_seconds: float
    timeout_seconds: float
    path_contains: str
    priority_substrings: tuple[str, ...]


def load_settings() -> CrawlSettings:
    return CrawlSettings(
        sitemap_url=os.getenv(
            "SITEMAP_URL",
            "https://support.brilliantdirectories.com/support/sitemap.xml",
        ),
        robots_url=os.getenv(
            "ROBOTS_URL",
            "https://support.brilliantdirectories.com/robots.txt",
        ),
        user_agent=os.getenv(
            "CRAWL_USER_AGENT",
            "AITechConsultant/0.1 (educational capstone; polite crawler)",
        ),
        max_pages=_env_int("INGEST_MAX_PAGES", 30),
        max_concurrency=_env_int("CRAWL_MAX_CONCURRENCY", 2),
        delay_seconds=_env_float("CRAWL_DELAY_SECONDS", 1.5),
        max_retries=_env_int("CRAWL_MAX_RETRIES", 4),
        retry_base_seconds=_env_float("CRAWL_RETRY_BASE_SECONDS", 1.0),
        timeout_seconds=_env_float("CRAWL_TIMEOUT_SECONDS", 30.0),
        path_contains=os.getenv("CRAWL_PATH_CONTAINS", "/solutions/articles/"),
        priority_substrings=tuple(
            part.strip().lower()
            for part in os.getenv("CRAWL_PRIORITY_SUBSTRINGS", "refund").split(",")
            if part.strip()
        ),
    )


@dataclass(frozen=True)
class EmbedSettings:
    model_name: str


def load_embed_settings() -> EmbedSettings:
    return EmbedSettings(
        model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
    )
