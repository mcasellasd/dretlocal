from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_key: str | None = os.getenv("SUPABASE_KEY")
    corpus_dir: Path = field(default_factory=lambda: BASE_DIR / "output_chunks")
    corpus_file: Path = field(
        default_factory=lambda: BASE_DIR / "output_chunks" / "cerdanya_ordenances_chunks.json"
    )
    max_citations: int = int(os.getenv("MAX_CITATIONS", "5"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))

    allowed_municipalities: tuple[str, ...] = (
        "alp",
        "bellver de cerdanya",
        "bolvir",
        "das",
        "fontanals de cerdanya",
        "ger",
        "guils de cerdanya",
        "isovol",
        "lles de cerdanya",
        "llivia",
        "meranges",
        "montella i martinet",
        "prats i sansor",
        "puigcerda",
        "riu de cerdanya",
        "urus",
    )

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)


settings = Settings()
