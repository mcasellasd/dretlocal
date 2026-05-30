import requests
from bs4 import BeautifulSoup
import re

url = "https://cido.diba.cat/normativa_local"
r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')
select = soup.find('select', {'name': 'codi_ens'})
if select:
    for opt in select.find_all('option'):
        print(f"{opt['value']}: {opt.text.strip()}")
        if 'Cerdanya' in opt.text or 'Alp' in opt.text or 'Bolvir' in opt.text:
            pass # we could filter, but let's just print a few or match our list

