from __future__ import annotations

from functools import lru_cache
import json
import re
import unicodedata

from app.config import settings


def _normalize(text: str) -> str:
    lowered = unicodedata.normalize("NFKD", text.lower())
    lowered = "".join(char for char in lowered if not unicodedata.combining(char))
    lowered = re.sub(r"[^a-z0-9\s-]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


@lru_cache(maxsize=1)
def load_corpus() -> list[dict]:
    candidates: list[Path] = []
    if settings.corpus_file.exists():
        candidates.append(settings.corpus_file)

    if settings.corpus_dir.exists():
        for path in sorted(settings.corpus_dir.glob("*_chunks.json")):
            if path not in candidates:
                candidates.append(path)

    loaded: list[dict] = []
    for path in candidates:
        try:
            with open(path, encoding="utf-8") as handle:
                raw = json.load(handle)
        except Exception:
            continue

        if isinstance(raw, list) and raw:
            loaded.extend(item for item in raw if isinstance(item, dict))

    return loaded


def corpus_size() -> int:
    return len(load_corpus())


def search_local(
    query: str,
    municipality: str | None = None,
    category: str | None = None,
    limit: int = 5,
) -> list[dict]:
    items = load_corpus()
    if not items:
        return []

    query_tokens = set(_normalize(query).split())
    municipality_norm = _normalize(municipality) if municipality else None
    category_norm = _normalize(category) if category else None

    scored: list[tuple[float, dict]] = []
    for item in items:
        chunk_text = item.get("chunk_text") or item.get("text_article") or ""
        haystack = _normalize(" ".join([chunk_text, item.get("nom_document", ""), item.get("municipi", "")]))
        haystack_tokens = set(haystack.split())
        overlap = len(query_tokens & haystack_tokens)
        if not overlap:
            continue

        score = float(overlap)

        if municipality_norm and municipality_norm in _normalize(item.get("municipi", "")):
            score += 1.5

        if category_norm:
            categories = " ".join(item.get("categories", []))
            if category_norm in _normalize(categories):
                score += 1.0

        scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def format_excerpt(item: dict, max_chars: int = 600) -> str:
    text = item.get("text_article") or item.get("chunk_text") or ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]
