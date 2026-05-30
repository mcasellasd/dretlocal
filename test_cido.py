import requests
import json

municipis = ["Alp", "Bolvir", "Das", "Fontanals de Cerdanya", "Ger", "Guils de Cerdanya", "Isòvol", "Lles de Cerdanya", "Llívia", "Meranges", "Montellà i Martinet", "Prats i Sansor", "Puigcerdà", "Riu de Cerdanya", "Urús", "Bellver de Cerdanya"]

for m in municipis:
    # try searching autocomplete
    r = requests.get(f"https://cido.diba.cat/api/ens/cerca?q={m}")
    print(f"{m}: {r.status_code}")
    if r.status_code == 200:
        try:
           print(r.json()[:2])
        except:
           pass
