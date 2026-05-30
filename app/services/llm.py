from __future__ import annotations

from typing import Sequence

from app.config import settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


def build_context_prompt(question: str, citations: Sequence[dict]) -> str:
    blocks = []
    for idx, citation in enumerate(citations, start=1):
        blocks.append(
            f"[{idx}] {citation.get('municipality', '')} | {citation.get('document_title', '')} | {citation.get('article_title') or ''}\n"
            f"{citation.get('excerpt', '')}"
        )
    context = "\n\n".join(blocks)
    return (
        "Ets un assistent juridic local especialitzat en legislacio municipal de Cerdanya. "
        "Respon nomes amb base en les fonts proporcionades. Si no hi ha prou base, digues-ho clarament. "
        "Cita les fonts usant els numeros entre claudators.\n\n"
        f"Pregunta: {question}\n\n"
        f"Fonts:\n{context}"
    )


def generate_answer(question: str, citations: Sequence[dict]) -> tuple[str, str]:
    if not citations:
        return (
            "No he trobat prou base documental dins la corpus de Cerdanya per respondre amb seguretat.",
            "low",
        )

    if OpenAI is None or not settings.has_openai:
        lines = [
            "Resposta preliminar basada en les fonts recuperades:",
            "",
        ]
        for idx, citation in enumerate(citations, start=1):
            lines.append(f"[{idx}] {citation.get('document_title', '')}: {citation.get('excerpt', '')}")
        lines.append("")
        lines.append("Aquesta resposta es pot reforcar quan activis l'API d'OpenAI.")
        return "\n".join(lines), "medium"

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = build_context_prompt(question, citations)
    response = client.responses.create(
        model=settings.openai_model,
        input=prompt,
    )
    answer_text = getattr(response, "output_text", None)
    if not answer_text:
        answer_text = "No he pogut generar una resposta utilitzable amb el model configurat."
    return answer_text, "high"
