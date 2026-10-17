"""Knowledge Brain HTTP API and a simple chat page."""

from __future__ import annotations

import sys
from pathlib import Path

TASK1_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TASK1_ROOT.parent
for path in (str(TASK1_ROOT), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ingestion.config import SQLITE_PATH, load_query_settings
from retrieval.embedder import MiniLMEmbedder
from retrieval.store import ChromaStore
from shared.llm import LLMClient, load_llm_settings

from .db import KnowledgeDB
from .query import ChromaRetriever, QueryService
from .schemas import (
    EscalationCreate,
    EscalationOut,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    ResolveRequest,
)

templates = Jinja2Templates(directory=str(TASK1_ROOT / "templates"))


def load_query_prompt() -> str:
    path = load_query_settings().prompt_path
    return path.read_text(encoding="utf-8")


def build_default_service() -> QueryService:
    embedder = MiniLMEmbedder()
    store = ChromaStore()
    return QueryService(
        db=KnowledgeDB(SQLITE_PATH),
        retriever=ChromaRetriever(embedder, store),
        llm=LLMClient(),
        store=store,
        embedder=embedder,
        prompt_loader=load_query_prompt,
    )


def create_app(service: QueryService | None = None) -> FastAPI:
    app = FastAPI(title="Knowledge Brain", version="0.3.0")
    app.state.service = service

    def get_service() -> QueryService:
        if app.state.service is None:
            app.state.service = build_default_service()
        return app.state.service

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        settings = load_llm_settings()
        store_count = 0
        try:
            store_count = get_service().store.count()
        except Exception:
            store_count = -1
        return HealthResponse(
            status="ok",
            llm_provider=settings.provider,
            llm_model=settings.model,
            store_count=store_count,
        )

    @app.get("/", response_class=HTMLResponse)
    async def chat_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request=request, name="chat.html", context={})

    @app.post("/query", response_model=QueryResponse)
    async def query(body: QueryRequest) -> QueryResponse:
        return await get_service().query(body.question)

    @app.post("/escalations", response_model=EscalationOut)
    async def create_escalation(body: EscalationCreate) -> EscalationOut:
        svc = get_service()
        escalation_id = svc.db.create_escalation(body.question, body.evidence, body.reason)
        row = svc.db.get_escalation(escalation_id)
        assert row is not None
        return EscalationOut.model_validate(row)

    @app.get("/escalations", response_model=list[EscalationOut])
    async def list_escalations() -> list[EscalationOut]:
        return [EscalationOut.model_validate(row) for row in get_service().db.list_open()]

    @app.post("/escalations/{escalation_id}/resolve", response_model=EscalationOut)
    async def resolve_escalation(escalation_id: int, body: ResolveRequest) -> EscalationOut:
        svc = get_service()
        try:
            row = svc.db.resolve_escalation(escalation_id, body.answer)
        except KeyError:
            raise HTTPException(status_code=404, detail="Unknown escalation") from None
        svc.index_expert_answer(
            question=row["question"],
            answer=body.answer,
            escalation_id=escalation_id,
            version=int(row["version"]),
        )
        # Drop cache so a later question can use the new expert chunk.
        svc.db.conn.execute("DELETE FROM query_cache")
        svc.db.conn.commit()
        return EscalationOut.model_validate(row)

    return app


app = create_app()
