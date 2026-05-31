import os
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Config
client_openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

def test_search(query, municipi=None):
    print(f"\n🔍 Cercant: '{query}'" + (f" a {municipi}" if municipi else ""))
    
    # 1. Generar embedding de la pregunta
    res_emb = client_openai.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    embedding = res_emb.data[0].embedding

    # 2. Crida a la funció RPC de Supabase
    params = {
        "query_embedding": embedding,
        "limit_n": 3
    }
    if municipi:
        params["municipi_filter"] = municipi

    res = supabase.rpc("cerca_chunks", params).execute()

    if not res.data:
        print("❌ No s'han trobat resultats.")
        return

    for i, row in enumerate(res.data):
        print(f"\n[{i+1}] {row['municipi']} - {row['nom_document']}")
        print(f"   Article: {row['titol_article']}")
        print(f"   Similitud: {row['similarity']:.4f}")
        # Mostrar els primers 200 caràcters del text
        snippet = row['text_article'][:200].replace('\n', ' ') + "..."
        print(f"   Text: {snippet}")


QUERIES_RAPIDES = [
    "ordenança neteja viària municipi",
    "article sorolls horari nocturn",
    "límits activitats molestes horari",
    "sanció mínima infracció lleu",
    "sanció màxima infracció greu",
    "ocupació via pública autorització",
    "manteniment neteja solars privats",
    "requisits instal·lació terrassa bar",
    "publicitat façanes permisos municipals",
    "tall carrer obres permís",
    "normativa tinença animals domèstics",
    "excrements gossos obligacions propietari",
    "recollida selectiva obligacions comerços",
    "pagament multa reducció termini",
    "al·legacions expedient sancionador termini",
]

if __name__ == "__main__":
    for query in QUERIES_RAPIDES:
        test_search(query)
