"""
Pipeline complet: CIDO scraping + chunking + JSON per a dretlocal.cat
Executa des de la teva màquina local:
    pip install requests beautifulsoup4 pdfplumber pandas tqdm
    python pipeline_ordenances.py
"""

import csv
import json
import re
import time
import hashlib
from collections import Counter
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import pdfplumber
import pandas as pd
from tqdm import tqdm

# ── Configuració ────────────────────────────────────────────────────────────
HEADERS = {"User-Agent": "DretLocal/1.0 (recerca academica; contact@dretlocal.cat)"}
OUTPUT_DIR = Path("output_chunks")
PDF_DIR    = Path("pdfs_cache")
OUTPUT_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)

CSV_INPUT = "Ordenances_cerdanya_complet.csv"

# Municipis de la Cerdanya (codi INE -> nom normalitzat)
MUNICIPIS_CERDANYA = {
    "1708280001": "Guils de Cerdanya",
    "1700630001": "Alp",
    "1700950001": "Bolvir",
    "1701430001": "Das",
    "1702450001": "Fontanals de Cerdanya",
    "1702620001": "Ger",
    "1704820001": "Isòvol",
    "1705120001": "Lles de Cerdanya",
    "1705290001": "Llívia",
    "1705570001": "Meranges",
    "1705880001": "Montellà i Martinet",
    "1707620001": "Prats i Sansor",
    "1707870001": "Puigcerdà",
    "1708210001": "Riu de Cerdanya",
    "1709270001": "Urús",
    "1701710001": "Bellver de Cerdanya",
    "1702820001": "Golmés",  # revisar
}

# Classificació automàtica per paraules clau al títol
CATEGORIES = {
    "urbanisme":    ["urbanístic", "edificació", "llicències", "sòl", "planejament", "POUM", "obra"],
    "medi_natural": ["medi natural", "forestal", "incendi", "accés motoritzat", "fauna", "flora"],
    "fiscal":       ["impost", "taxa", "contribució", "fiscal", "tribut", "preu públic"],
    "circulacio":   ["circulació", "vehicle", "trànsit", "gual", "estacionament"],
    "serveis":      ["aigua", "abastament", "subministrament", "residus", "clavegueram"],
    "participacio": ["participació", "reglament orgànic", "cartipàs", "grups municipals"],
    "activitats":   ["activitat", "llicència ambiental", "soroll", "horaris"],
    "rural":        ["fems", "purins", "pastures", "ramaderia", "agrícola", "reg"],
    "esqui":        ["esquí", "nòrdic", "estació", "neu"],
    "habitatge":    ["habitatge", "allotjament", "turisme rural", "apartament"],
}

def classificar(titol: str) -> list[str]:
    titol_lower = titol.lower()
    cats = [cat for cat, kws in CATEGORIES.items() if any(kw in titol_lower for kw in kws)]
    return cats if cats else ["general"]

def generar_id(municipi: str, titol: str, article: str = "") -> str:
    base = f"{municipi}-{titol}-{article}"
    return hashlib.md5(base.encode()).hexdigest()[:12]

def municipi_slug(nom: str) -> str:
    return nom.lower().replace(" ", "-").replace("'", "").replace("à","a").replace("è","e").replace("é","e").replace("í","i").replace("ï","i").replace("ó","o").replace("ò","o").replace("ú","u").replace("ü","u")


ALLOWED_MUNICIPI_SLUGS = {
    municipi_slug(f"Ajuntament de {nom}")
    for nom in MUNICIPIS_CERDANYA.values()
    if "Mancomunitat" not in nom
}

# ── 1. Carregar CSV ──────────────────────────────────────────────────────────
def carregar_csv(path: str) -> list[dict]:
    docs = []
    vistos = set()
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("VIGENT", "").lower() != "true":
                continue

            municipi = (row.get("NOM_ENS") or "").strip()
            slug = municipi_slug(municipi)
            if slug not in ALLOWED_MUNICIPI_SLUGS:
                continue

            url = (row.get("ENLLAÇ") or "").strip()
            if not url.startswith("https://cido.diba.cat/normativa_local/"):
                continue

            if url in vistos:
                continue

            vistos.add(url)
            docs.append(row)

    print(f"Documents vigents Cerdanya carregats: {len(docs)}")
    return docs


def guardar_informe_cobertura(docs: list[dict], chunks: list[dict], errors: list[dict]) -> None:
    input_urls = {(d.get("ENLLAÇ") or "").strip() for d in docs if d.get("ENLLAÇ")}
    chunk_urls = {(c.get("url_oficial") or "").strip() for c in chunks if c.get("url_oficial")}
    error_urls = {(e.get("url") or "").strip() for e in errors if e.get("url")}

    municipis_input = Counter((d.get("NOM_ENS") or "").strip() for d in docs)
    municipis_chunks = Counter((c.get("municipi") or "").strip() for c in chunks)

    informe = {
        "docs_input": len(docs),
        "docs_input_unics": len(input_urls),
        "docs_amb_chunks": len(input_urls & chunk_urls),
        "docs_sense_chunks": len(input_urls - chunk_urls),
        "docs_amb_error": len(error_urls),
        "municipis_input": municipis_input,
        "municipis_chunks": municipis_chunks,
        "urls_sense_chunks_sample": sorted(list(input_urls - chunk_urls))[:50],
    }

    output = OUTPUT_DIR / "coverage_report.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(informe, f, ensure_ascii=False, indent=2)
    print(f"✓ Informe de cobertura: {output}")

# ── 2. Scraping CIDO ─────────────────────────────────────────────────────────
def scrape_cido(url: str) -> dict:
    """
    Retorna {'text': str, 'pdf_url': str|None, 'tipus_fitxer': str}
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        return {"text": "", "pdf_url": None, "tipus_fitxer": "error"}

    soup = BeautifulSoup(r.text, "html.parser")

    # Buscar PDF directe
    pdf_url = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf") or "pdf" in href.lower():
            pdf_url = href if href.startswith("http") else "https://cido.diba.cat" + href
            break

    # Text directe a la pàgina
    main = (soup.find("div", class_="field-items") or
            soup.find("article") or
            soup.find("main") or
            soup.find("div", id="content"))
    text = main.get_text(separator="\n", strip=True) if main else ""

    return {
        "text": text,
        "pdf_url": pdf_url,
        "tipus_fitxer": "pdf" if pdf_url else "html"
    }

# ── 3. Extreure text de PDF ──────────────────────────────────────────────────
def extreure_pdf(pdf_url: str, cache_path: Path) -> str:
    if cache_path.exists():
        with pdfplumber.open(cache_path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)

    try:
        r = requests.get(pdf_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        cache_path.write_bytes(r.content)
        with pdfplumber.open(cache_path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        print(f"  Error PDF {pdf_url}: {e}")
        return ""

# ── 4. Chunking per article ──────────────────────────────────────────────────
PATRONS_ARTICLE = [
    re.compile(r"(Article\s+\d+[\w\s\.\-àèéíïóòúü,]*?)\n(.*?)(?=Article\s+\d+|\Z)", re.DOTALL | re.IGNORECASE),
    re.compile(r"(Art\.\s*\d+[\w\s\.\-àèéíïóòúü,]*?)\n(.*?)(?=Art\.\s*\d+|\Z)", re.DOTALL | re.IGNORECASE),
    re.compile(r"(Secció\s+\w+[\w\s\.\-àèéíïóòúü,]*?)\n(.*?)(?=Secció\s+\w+|\Z)", re.DOTALL | re.IGNORECASE),
]

def extreure_articles(text: str) -> list[dict]:
    """Retorna llista de {titol_article, num_article, text_article}"""
    articles = []
    for patro in PATRONS_ARTICLE:
        matches = list(patro.finditer(text))
        if len(matches) >= 2:  # mínim 2 articles per considerar vàlid
            for m in matches:
                titol = m.group(1).strip()
                cos   = m.group(2).strip()[:3000]
                num   = re.search(r"\d+", titol)
                articles.append({
                    "titol_article": titol,
                    "num_article": num.group() if num else "0",
                    "text_article": cos,
                })
            return articles

    # Si no hi ha articles detectats, tractar tot com un sol chunk
    if text.strip():
        articles.append({
            "titol_article": "Document complet",
            "num_article": "0",
            "text_article": text.strip()[:4000],
        })
    return articles

def detectar_jerarquia(text: str, posicio: int) -> dict:
    """Detecta el Títol i Capítol vigent en un punt del text"""
    fragment = text[:posicio]
    titol = ""
    capitol = ""
    for linia in fragment.split("\n"):
        l = linia.strip()
        if re.match(r"^(TÍTOL|TITOL|Títol)\s+[IVX\d]+", l, re.IGNORECASE):
            titol = l
            capitol = ""
        elif re.match(r"^(CAPÍTOL|CAPITOL|Capítol)\s+[IVX\d]+", l, re.IGNORECASE):
            capitol = l
    return {"titol": titol, "capitol": capitol}

# ── 5. Generar chunk JSON ─────────────────────────────────────────────────────
def generar_chunks(doc: dict, text: str, metadades_extra: dict) -> list[dict]:
    municipi    = doc["NOM_ENS"]
    slug        = municipi_slug(municipi)
    titol_doc   = doc["RESUM"]
    data_pub    = doc["DATA_PUB"][:10] if doc["DATA_PUB"] else ""
    url_oficial = doc["ENLLAÇ"]
    categories  = classificar(titol_doc)
    lat         = doc.get("LATITUD", "")
    lon         = doc.get("LONGITUD", "")

    resum_doc = f"{titol_doc} — {municipi}, vigent des de {data_pub}."

    articles = extreure_articles(text)
    chunks = []

    for art in articles:
        chunk_text = (
            f"{municipi} · {titol_doc} · {art['titol_article']}. "
            f"{art['text_article']}"
        )

        chunk = {
            "id": generar_id(slug, titol_doc, art["num_article"]),
            "tipus_document": "ordenanca",
            "municipi": municipi,
            "municipi_slug": slug,
            "comarca": "Cerdanya",
            "nom_document": titol_doc,
            "categories": categories,
            "data_publicacio": data_pub,
            "vigent": True,
            "url_oficial": url_oficial,
            "coordenades": {"lat": lat, "lon": lon},
            "jerarquia": {
                "titol": art.get("jerarquia_titol", ""),
                "capitol": art.get("jerarquia_capitol", ""),
                "article": art["titol_article"],
                "num_article": art["num_article"],
            },
            "text_article": art["text_article"],
            "resum_document": resum_doc,
            "chunk_text": chunk_text[:2500],  # límit recomanat per embedding
            "tokens_aprox": len(chunk_text.split()),
            "proces_data": datetime.now().isoformat(),
        }
        chunks.append(chunk)

    return chunks

# ── 6. Pipeline principal ────────────────────────────────────────────────────
def main():
    docs = carregar_csv(CSV_INPUT)
    tots_chunks = []
    errors = []

    for doc in tqdm(docs, desc="Processant documents"):
        url = doc["ENLLAÇ"]
        municipi = doc["NOM_ENS"]

        # Scraping
        resultat = scrape_cido(url)
        time.sleep(1)  # respectar el servidor

        text = resultat["text"]

        # Si hi ha PDF, extreure'n el text
        if resultat["pdf_url"]:
            nom_cache = PDF_DIR / f"{generar_id(municipi, url)}.pdf"
            text_pdf = extreure_pdf(resultat["pdf_url"], nom_cache)
            if text_pdf:
                text = text_pdf  # PDF té prioritat sobre HTML

        if not text.strip():
            errors.append({"url": url, "motiu": "sense text"})
            continue

        chunks = generar_chunks(doc, text, {})
        tots_chunks.extend(chunks)

    # Guardar JSON complet
    output_path = OUTPUT_DIR / "cerdanya_ordenances_chunks.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tots_chunks, f, ensure_ascii=False, indent=2)

    # Guardar també per municipi (un fitxer per municipi)
    per_municipi = {}
    for chunk in tots_chunks:
        slug = chunk["municipi_slug"]
        per_municipi.setdefault(slug, []).append(chunk)

    for slug, chunks in per_municipi.items():
        path = OUTPUT_DIR / f"{slug}_chunks.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

    # Resum
    print(f"\n✓ Chunks generats: {len(tots_chunks)}")
    print(f"✓ Documents amb error: {len(errors)}")
    print(f"✓ Municipis: {len(per_municipi)}")
    print(f"✓ Output: {output_path}")

    if errors:
        with open(OUTPUT_DIR / "errors.json", "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        print(f"✗ Errors guardats a errors.json")

    guardar_informe_cobertura(docs, tots_chunks, errors)

    # Estadístiques
    df = pd.DataFrame(tots_chunks)
    print("\n── Chunks per municipi ──")
    print(df.groupby("municipi").size().sort_values(ascending=False).to_string())
    print("\n── Chunks per categoria ──")
    cats = df["categories"].explode()
    print(cats.value_counts().to_string())

if __name__ == "__main__":
    main()
