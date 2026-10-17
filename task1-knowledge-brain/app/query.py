"""Answer a question from retrieved chunks, or escalate when evidence is weak."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from ingestion.config import load_query_settings
from retrieval.chunk import Chunk, stable_chunk_id
from retrieval.store import SearchHit
from shared.llm import LLMError
from shared.untrusted import wrap_untrusted

from .db import KnowledgeDB
from .schemas import QueryResponse, Source


class Retriever(Protocol):
    def search(self, question: str, k: int) -> list[SearchHit]: ...


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class Store(Protocol):
    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None: ...

    def count(self) -> int: ...


class LLM(Protocol):
    async def generate(self, *, system: str, user: str) -> str: ...


def relevance_from_distance(distance: float) -> float:
    return round(max(0.0, min(1.0, 1.0 - distance)), 4)


def sources_from_hits(hits: list[SearchHit]) -> list[Source]:
    seen: set[str] = set()
    sources: list[Source] = []
    for hit in hits:
        if not hit.url or hit.url in seen:
            continue
        seen.add(hit.url)
        sources.append(
            Source(
                title=hit.title or hit.url,
                url=hit.url,
                relevance=relevance_from_distance(hit.distance),
            )
        )
    return sources


def image_refs_from_hits(hits: list[SearchHit]) -> list[str]:
    refs: list[str] = []
    for hit in hits:
        for part in (hit.image_urls or "").split(" | "):
            url = part.strip()
            if url and url not in refs:
                refs.append(url)
    return refs


def format_evidence(hits: list[SearchHit]) -> str:
    blocks: list[str] = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(
            f"Source {i}\n"
            f"title: {hit.title}\n"
            f"url: {hit.url}\n"
            f"section: {hit.section_heading}\n"
            f"text:\n{hit.text}"
        )
    return "\n\n".join(blocks)


class ChromaRetriever:
    def __init__(self, embedder: Embedder, store: Any) -> None:
        self.embedder = embedder
        self.store = store

    def search(self, question: str, k: int) -> list[SearchHit]:
        vector = self.embedder.encode([question])[0]
        return self.store.query(vector, k=k)


class QueryService:
    def __init__(
        self,
        *,
        db: KnowledgeDB,
        retriever: Retriever,
        llm: LLM,
        store: Store,
        embedder: Embedder,
        prompt_loader: Callable[[], str],
        top_k: int | None = None,
        max_distance: float | None = None,
    ) -> None:
        settings = load_query_settings()
        self.db = db
        self.retriever = retriever
        self.llm = llm
        self.store = store
        self.embedder = embedder
        self.prompt_loader = prompt_loader
        self.top_k = top_k if top_k is not None else settings.top_k
        self.max_distance = (
            max_distance if max_distance is not None else settings.max_distance
        )

    async def query(self, question: str) -> QueryResponse:
        question = question.strip()
        cached = self.db.get_cached(question)
        if cached:
            return QueryResponse.model_validate(cached)

        hits = self.retriever.search(question, self.top_k)
        if not hits or hits[0].distance > self.max_distance:
            evidence = format_evidence(hits)
            reason = (
                "no retrieved chunks"
                if not hits
                else f"best distance {hits[0].distance:.4f} > {self.max_distance}"
            )
            escalation_id = self.db.create_escalation(question, evidence, reason)
            response = QueryResponse(
                answer="I don't know. There is not enough evidence in the help center, so this was sent to a human expert.",
                status="insufficient_evidence",
                sources=sources_from_hits(hits),
                image_refs=image_refs_from_hits(hits),
                needs_human=True,
                escalation_id=escalation_id,
            )
            self.db.put_cached(question, response.model_dump())
            return response

        system = self.prompt_loader()
        user = wrap_untrusted("untrusted_evidence", format_evidence(hits))
        user += f"\n\nQuestion: {question}"
        try:
            answer = await self.llm.generate(system=system, user=user)
        except LLMError as exc:
            return QueryResponse(
                answer=str(exc),
                status="error",
                sources=sources_from_hits(hits),
                image_refs=image_refs_from_hits(hits),
                needs_human=False,
                escalation_id=None,
            )

        response = QueryResponse(
            answer=answer,
            status="answered",
            sources=sources_from_hits(hits),
            image_refs=image_refs_from_hits(hits),
            needs_human=False,
            escalation_id=None,
        )
        self.db.put_cached(question, response.model_dump())
        return response

    def index_expert_answer(self, *, question: str, answer: str, escalation_id: int, version: int) -> None:
        url = f"expert://escalation/{escalation_id}/v{version}"
        title = "Expert answer (reviewed)"
        chunk = Chunk(
            chunk_id=stable_chunk_id(url, "Expert", 0),
            url=url,
            title=title,
            section_heading="Expert",
            text=f"Question: {question}\nAnswer: {answer}",
            images=[],
            chunk_index=0,
        )
        document = chunk.embed_text()
        embedding = self.embedder.encode([document])[0]
        metadata = chunk.to_metadata()
        metadata["reviewed"] = "true"
        metadata["source_type"] = "expert"
        self.store.upsert(
            ids=[chunk.chunk_id],
            documents=[document],
            metadatas=[metadata],
            embeddings=[embedding],
        )
