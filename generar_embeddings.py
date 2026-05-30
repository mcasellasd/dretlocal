"""
Genera embeddings dels chunks i els puja a Supabase amb pgvector.
Executa després de pipeline_ordenances.py.

    pip install openai supabase tqdm
    python generar_embeddings.py

Variables d'entorn necessàries:
    OPENAI_API_KEY=sk-...
    SUPABASE_URL=https://xxx.supabase.co
    SUPABASE_KEY=eyJ...
"""

import json
import os
import time
from pathlib import Path
from tqdm import tqdm
from openai import OpenAI
from supabase import create_client

# ── Config ──────────────────────────────────────────────────────────────────
CHUNKS_PATH   = Path("output_chunks/cerdanya_ordenances_chunks.json")
BATCH_SIZE    = 100   # chunks per crida d'embedding
EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dims, barat i bo en català

client_openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)

# ── SQL per crear la taula (executa una vegada a Supabase SQL Editor) ────────
SCHEMA_SQL = """
-- Habilitar extensió pgvector
create extension if not exists vector;

-- Taula principal de chunks
create table if not exists chunks_ordenances (
    id              text primary key,
    tipus_document  text,
    municipi        text,
    municipi_slug   text,
    comarca         text,
    nom_document    text,
    categories      text[],
    data_publicacio date,
    vigent          boolean default true,
    url_oficial     text,
    jerarquia       jsonb,
    text_article    text,
    resum_document  text,
    chunk_text      text,
    tokens_aprox    int,
    embedding       vector(1536),
    created_at      timestamptz default now()
);

-- Índex vectorial per cerca semàntica
create index if not exists idx_chunks_embedding
    on chunks_ordenances
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

-- Índex per filtre de municipi
create index if not exists idx_chunks_municipi
    on chunks_ordenances (municipi_slug);

-- Índex per filtre de categoria
create index if not exists idx_chunks_categories
    on chunks_ordenances using gin (categories);

-- Funció de cerca semàntica amb filtres opcionals
create or replace function cerca_chunks(
    query_embedding vector(1536),
    municipi_filter text default null,
    categoria_filter text default null,
    limit_n int default 5
)
returns table (
    id text,
    municipi text,
    nom_document text,
    titol_article text,
    text_article text,
    url_oficial text,
    similarity float
)
language sql stable
as $$
    select
        id,
        municipi,
        nom_document,
        jerarquia->>'article' as titol_article,
        text_article,
        url_oficial,
        1 - (embedding <=> query_embedding) as similarity
    from chunks_ordenances
    where vigent = true
      and (municipi_filter is null or municipi_slug = municipi_filter)
      and (categoria_filter is null or categoria_filter = any(categories))
    order by embedding <=> query_embedding
    limit limit_n;
$$;
"""

def generar_embeddings_batch(textos: list[str]) -> list[list[float]]:
    """Genera embeddings per un batch de textos."""
    resposta = client_openai.embeddings.create(
        model=EMBEDDING_MODEL,
        input=textos
    )
    return [item.embedding for item in resposta.data]

def pujar_chunks(chunks: list[dict]):
    """Puja chunks a Supabase en batches."""

    # Filtrar els que ja existeixen (per ID)
    ids_existents = set()
    try:
        res = supabase.table("chunks_ordenances").select("id").execute()
        ids_existents = {r["id"] for r in res.data}
        print(f"Chunks ja existents: {len(ids_existents)}")
    except:
        pass

    nous_chunks = [c for c in chunks if c["id"] not in ids_existents]
    print(f"Chunks nous a processar: {len(nous_chunks)}")

    for i in tqdm(range(0, len(nous_chunks), BATCH_SIZE), desc="Embeddings + upload"):
        batch = nous_chunks[i:i + BATCH_SIZE]
        textos = [c["chunk_text"] for c in batch]

        try:
            embeddings = generar_embeddings_batch(textos)
        except Exception as e:
            print(f"Error embedding batch {i}: {e}")
            time.sleep(5)
            continue

        rows = []
        for chunk, emb in zip(batch, embeddings):
            rows.append({
                "id":              chunk["id"],
                "tipus_document":  chunk["tipus_document"],
                "municipi":        chunk["municipi"],
                "municipi_slug":   chunk["municipi_slug"],
                "comarca":         chunk["comarca"],
                "nom_document":    chunk["nom_document"],
                "categories":      chunk["categories"],
                "data_publicacio": chunk["data_publicacio"] or None,
                "vigent":          chunk["vigent"],
                "url_oficial":     chunk["url_oficial"],
                "jerarquia":       chunk["jerarquia"],
                "text_article":    chunk["text_article"],
                "resum_document":  chunk["resum_document"],
                "chunk_text":      chunk["chunk_text"],
                "tokens_aprox":    chunk["tokens_aprox"],
                "embedding":       emb,
            })

        try:
            supabase.table("chunks_ordenances").upsert(rows).execute()
        except Exception as e:
            print(f"Error upload batch {i}: {e}")

        time.sleep(0.5)  # rate limit openai

def main():
    print("── Carregant chunks ──")
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Total chunks: {len(chunks)}")

    print("\n── Pujant a Supabase ──")
    print("(Assegura't d'haver executat el SQL de SCHEMA_SQL a Supabase primer)")
    pujar_chunks(chunks)

    print("\n✓ Fet. Pots cercar amb la funció cerca_chunks() des de la teva app.")
    print("\nExemple de cerca des de Next.js:")
    print("""
    const { data } = await supabase.rpc('cerca_chunks', {
      query_embedding: await getEmbedding(userQuery),
      municipi_filter: 'puigcerda',
      limit_n: 5
    })
    """)

if __name__ == "__main__":
    main()
