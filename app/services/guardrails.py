from __future__ import annotations

import unicodedata

from app.config import settings


def normalize_place(text: str | None) -> str:
    if not text:
        return ""
    lowered = unicodedata.normalize("NFKD", text.lower())
    lowered = "".join(char for char in lowered if not unicodedata.combining(char))
    return (
        lowered
        .replace("l'", "l")
        .replace("'", "")
    )


def is_in_scope(municipality: str | None) -> bool:
    if not municipality:
        return True
    normalized = normalize_place(municipality)
    return any(allowed in normalized for allowed in settings.allowed_municipalities)


def refusal_message(question: str) -> str:
    return (
        "No puc donar una resposta fiable per a aquest cas fora de l'ambit inicial de Cerdanya o sense base normativa suficient. "
        "Si vols, reformula la consulta per a un municipi de Cerdanya o aporta la norma concreta que vols contrastar."
    )
