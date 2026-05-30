from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str
    municipality: str | None = None
    category: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)


class Citation(BaseModel):
    id: str
    municipality: str
    document_title: str
    article_title: str | None = None
    url: str | None = None
    similarity: float | None = None
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: str
    territory: str
    refusal: bool = False


class SearchRequest(BaseModel):
    query: str
    municipality: str | None = None
    category: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class SearchHit(BaseModel):
    id: str
    municipality: str
    document_title: str
    article_title: str | None = None
    url: str | None = None
    similarity: float | None = None
    excerpt: str


class SearchResponse(BaseModel):
    hits: list[SearchHit]


class HealthResponse(BaseModel):
    status: str
    corpus_ready: bool
    corpus_size: int
    openai_ready: bool
    supabase_ready: bool
