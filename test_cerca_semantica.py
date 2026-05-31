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

if __name__ == "__main__":
    # Test 1: Cerca general sobre tancaments o rural
    test_search("normativa sobre pastures i fems")
    
    # Test 2: Cerca específica per municipi
    test_search("venda ambulant", municipi="puigcerda")
    
    # Test 3: Cerca sobre convivència
    test_search("sorolls i descans veïnal")
