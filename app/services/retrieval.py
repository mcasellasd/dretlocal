from __future__ import annotations

from typing import Any

from app.config import settings
from app.services.corpus import format_excerpt, search_local

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None


def _get_supabase_client():
    if not settings.has_supabase or create_client is None:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)


def search_chunks(
    query: str,
    municipality: str | None = None,
    category: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    client = _get_supabase_client()
    if client is not None and OpenAI is not None:
        try:
            embedding_client = OpenAI(api_key=settings.openai_api_key)
            embedding = embedding_client.embeddings.create(
                model="text-embedding-3-small",
                input=query,
            ).data[0].embedding

            response = client.rpc(
                "cerca_chunks",
                {
                    "query_embedding": embedding,
                    "municipi_filter": municipality,
                    "categoria_filter": category,
                    "limit_n": limit,
                },
            ).execute()

            rows = response.data or []
            if rows:
                return [
                    {
                        "id": row.get("id"),
                        "municipality": row.get("municipi"),
                        "document_title": row.get("nom_document"),
                        "article_title": row.get("titol_article"),
                        "url": row.get("url_oficial"),
                        "similarity": row.get("similarity"),
                        "excerpt": row.get("text_article") or "",
                    }
                    for row in rows
                ]
        except Exception:
            pass

    results = search_local(query, municipality=municipality, category=category, limit=limit)
    return [
        {
            "id": item.get("id", ""),
            "municipality": item.get("municipi", ""),
            "document_title": item.get("nom_document", ""),
            "article_title": (item.get("jerarquia") or {}).get("article"),
            "url": item.get("url_oficial"),
            "similarity": None,
            "excerpt": format_excerpt(item),
        }
        for item in results
    ]
