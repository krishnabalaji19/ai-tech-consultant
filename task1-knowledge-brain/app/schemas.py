"""Request and response shapes for the Knowledge Brain API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

QueryStatus = Literal["answered", "insufficient_evidence", "error"]
EscalationStatus = Literal["open", "resolved"]


class Source(BaseModel):
    title: str
    url: str
    relevance: float = Field(
        description="1 minus cosine distance. Not a calibrated confidence score."
    )


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)


class QueryResponse(BaseModel):
    answer: str
    status: QueryStatus
    sources: list[Source]
    image_refs: list[str]
    needs_human: bool
    escalation_id: int | None = None


class EscalationCreate(BaseModel):
    question: str = Field(min_length=1)
    evidence: str = ""
    reason: str = "manual"


class EscalationOut(BaseModel):
    id: int
    question: str
    evidence: str
    reason: str
    status: EscalationStatus
    created_at: str
    resolved_at: str | None = None
    version: int = 0


class ResolveRequest(BaseModel):
    answer: str = Field(min_length=1)


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    llm_model: str
    store_count: int
