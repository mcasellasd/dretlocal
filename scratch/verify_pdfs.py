import os
from pathlib import Path
import csv

pdf_dir = Path("pdfs_cache")
pdfs = list(pdf_dir.glob("*.pdf"))

total = len(pdfs)
small_files = 0
invalid_pdf_signatures = 0
valid = 0

for p in pdfs:
    size = p.stat().st_size
    if size < 1000:
        small_files += 1
        continue
        
    try:
        with open(p, "rb") as f:
            sig = f.read(4)
            if sig != b"%PDF":
                invalid_pdf_signatures += 1
            else:
                valid += 1
    except Exception as e:
        invalid_pdf_signatures += 1

print(f"Total PDFs in cache: {total}")
print(f"Small files (<1KB): {small_files}")
print(f"Invalid PDF signature: {invalid_pdf_signatures}")
print(f"Valid PDFs: {valid}")
