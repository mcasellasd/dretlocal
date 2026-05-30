import requests
from bs4 import BeautifulSoup

url = "https://cido.diba.cat/normativa_local?filtreParaulaClau%5Bkeyword%5D=cerdanya&filtreParaulaClau%5Bsubmit%5D=&ordenacio=DATAPUBLICACIO&ordre=DESC&showAs=GRID&filtreNormativaVigent%5Bvigent%5D=1&filtreProximitat%5Bpoblacio%5D=&filtreProximitat%5Bkm%5D=&filtreProximitat%5Blatitud%5D=&filtreProximitat%5Blongitud%5D=&filtreDataPublicacio%5Bde%5D=&filtreDataPublicacio%5BfinsA%5D=&opcions-menu=&_token=qHIPdSWxBRNVYnHOfdkkNo0bFNhCA91bGn8NhoNUJOM"

r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

items = soup.select('.views-row, .normativa-item, article, .item, .card')
print(f"Total elements trobats b\u00e0sics: {len(items)}")

# Let's try to find exactly where the results are
results = soup.select('a')
c=0
for a in results:
    if 'normativa_local/' in a.get('href', ''):
        c+=1
print("Links a normativa_local:", c)

# Let's inspect the pagination
page_links = soup.select('.pagination a, .pager a')
print("Paginacio links:", [a.get('href') for a in page_links])
