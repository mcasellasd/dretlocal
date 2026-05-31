import requests
import pandas as pd
import time
from tqdm import tqdm
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# Codis CIDO oficials dels 17 municipis de la Cerdanya catalana
MUNICIPIS_CERDANYA = {
    "1700630001": "Alp",
    "2505180001": "Bellver de Cerdanya",
    "1702420002": "Bolvir",
    "1706170005": "Das",
    "1706940003": "Fontanals de Cerdanya",
    "1707890004": "Ger",
    "1708280001": "Guils de Cerdanya",
    "1704820001": "Isòvol",
    "2512720002": "Lles de Cerdanya",
    "1709470005": "Llívia",
    "1709980001": "Meranges",
    "2513990004": "Montellà i Martinet",
    "2517520002": "Prats i Sansor",
    "2517900003": "Prullans",
    "1714110007": "Puigcerdà",
    "2591390004": "Riu de Cerdanya",
    "1709270001": "Urús"
}

def es_enllac_normativa_local(href: str) -> bool:
    if not href:
        return False
    parsed = urlparse(href)
    return parsed.netloc in {"cido.diba.cat", "www.cido.diba.cat"} and "/normativa_local/" in parsed.path


def descarregar_per_municipi(codi_ine: str, nom: str) -> list[dict]:
    docs = []
    vistos = set()
    try:
        from bs4 import BeautifulSoup
        page = 1
        
        while True:
            url_cerca = f"https://cido.diba.cat/normativa_local?filtreMunicipi%5Boptions%5D%5B%5D={codi_ine}&filtreNormativaVigent%5Bvigent%5D=1&page={page}"
            r = requests.get(url_cerca, headers=HEADERS, timeout=20)
            if r.status_code != 200: break
            soup = BeautifulSoup(r.text, "html.parser")
            
            links = soup.find_all("a", href=True)
            noves_docs = 0
            
            for link in links:
                href = link["href"]
                if 'normativa_local/' not in href: continue
                if not href.startswith("http"): href = "https://cido.diba.cat" + href
                if not es_enllac_normativa_local(href):
                    continue
                if href in vistos:
                    continue
                
                titol = link.get_text(strip=True)
                if not titol or titol.lower() in ['llegir més', 'més info']: continue
                
                data = ""
                parent = link.find_parent(['div', 'li', 'article'])
                if parent:
                    data_el = parent.find(class_=lambda x: x and "date" in x.lower())
                    if data_el: data = data_el.get_text(strip=True)
                
                docs.append({
                    "RESUM": titol, "DATA_PUB": data, "ENLLAÇ": href,
                    "CODI_ENS": codi_ine, "NOM_ENS": f"Ajuntament de {nom}" if "Mancomunitat" not in nom else nom,
                    "VIGENT": "True", "LATITUD": "", "LONGITUD": "",
                })
                vistos.add(href)
                noves_docs += 1
                
            if noves_docs == 0: break
            page += 1
            time.sleep(1)
            
    except Exception as e: print(f"  Error {nom}: {e}")
    return docs

def main():
    tots_docs = []
    print("Iniciant descàrrega intensiva des de la web de CIDO (tots els reglaments)...")
    for codi, nom in tqdm(MUNICIPIS_CERDANYA.items(), desc="Municipis"):
        docs = descarregar_per_municipi(codi, nom)
        tots_docs.extend(docs)
        print(f"  {nom}: {len(docs)} documents trobats")
        time.sleep(2)

    df = pd.DataFrame(tots_docs)
    if not df.empty:
        df = df.drop_duplicates(subset=["ENLLAÇ"])
        df.to_csv("Ordenances_cerdanya_complet.csv", index=False, encoding="utf-8-sig")
        print(f"\n✓ Guardat a Ordenances_cerdanya_complet.csv amb {len(df)} registres!")

if __name__ == "__main__":
    main()
