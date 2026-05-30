from __future__ import annotations

from fastapi import FastAPI

from app.config import settings
from app.schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    HealthResponse,
    SearchRequest,
    SearchResponse,
    SearchHit,
)
from app.services.corpus import corpus_size
from app.services.guardrails import is_in_scope, refusal_message
from app.services.llm import generate_answer
from app.services.retrieval import search_chunks


app = FastAPI(
    title="Dret Local Cerdanya API",
    version="0.1.0",
    description="Backend inicial per a consultes juridiques locals amb RAG i guardrails.",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    size = corpus_size()
    return HealthResponse(
        status="ok",
        corpus_ready=size > 0,
        corpus_size=size,
        openai_ready=settings.has_openai,
        supabase_ready=settings.has_supabase,
    )


@app.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest) -> SearchResponse:
    hits = search_chunks(
        payload.query,
        municipality=payload.municipality,
        category=payload.category,
        limit=payload.limit,
    )
    return SearchResponse(
        hits=[
            SearchHit(
                id=hit["id"],
                municipality=hit["municipality"],
                document_title=hit["document_title"],
                article_title=hit.get("article_title"),
                url=hit.get("url"),
                similarity=hit.get("similarity"),
                excerpt=hit.get("excerpt", ""),
            )
            for hit in hits
        ]
    )


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    if not is_in_scope(payload.municipality):
        return ChatResponse(
            answer=refusal_message(payload.question),
            citations=[],
            confidence="low",
            territory="out_of_scope",
            refusal=True,
        )

    citations_raw = search_chunks(
        payload.question,
        municipality=payload.municipality,
        category=payload.category,
        limit=settings.max_citations,
    )
    answer, confidence = generate_answer(payload.question, citations_raw)

    citations = [
        Citation(
            id=hit["id"],
            municipality=hit["municipality"],
            document_title=hit["document_title"],
            article_title=hit.get("article_title"),
            url=hit.get("url"),
            similarity=hit.get("similarity"),
            excerpt=hit.get("excerpt", ""),
        )
        for hit in citations_raw
    ]

    return ChatResponse(
        answer=answer,
        citations=citations,
        confidence=confidence,
        territory="cerdanya",
        refusal=False,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)