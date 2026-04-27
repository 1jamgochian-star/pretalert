import requests
from bs4 import BeautifulSoup
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

url = "https://www.emag.ro/search/samsung+galaxy+watch"
r = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(r.text, 'html.parser')
produse = soup.select('.card-item')
print(f"Produse: {len(produse)}")
for p in produse[:3]:
    nume = p.select_one('.card-v2-title')
    pret = p.select_one('.product-new-price')
    link = p.select_one('a.js-product-url')
    print(f"Nume: {nume.text.strip()[:50] if nume else 'N/A'}")
    print(f"Pret: {pret.text.strip() if pret else 'N/A'}")
    print(f"Link: {link['href'][:50] if link else 'N/A'}")
    print("---")
