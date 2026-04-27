import requests
import asyncio
from bs4 import BeautifulSoup
from database import salveaza_produs
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ro-RO,ro;q=0.9',
}

def extrage_emag_id(link):
    match = re.search(r'/pd/([A-Z0-9]+)/', link)
    return match.group(1) if match else link.split('/')[-2]

def curata_pret(pret_text):
    pret_text = pret_text.replace('Lei', '').replace('lei', '').strip()
    pret_text = pret_text.replace('.', '').replace(',', '.')
    pret_text = re.sub(r'[^\d.]', '', pret_text)
    try:
        return float(pret_text)
    except:
        return None

async def cauta_emag(query, pagina=1):
    if pagina == 1:
        emag_url = f"https://www.emag.ro/search/{query.replace(' ', '+')}"
    else:
        emag_url = f"https://www.emag.ro/search/{query.replace(' ', '+')}/p{pagina}/c"
    try:
        r = requests.get(emag_url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        produse = soup.select('.card-item')
        rezultate = []
        for p in produse:
            nume = p.select_one('.card-v2-title')
            pret = p.select_one('.product-new-price')
            link = p.select_one('a.js-product-url')
            if not nume or not pret or not link:
                continue
            poza = p.select_one('img')
            poza_url = None
            if poza:
                poza_url = poza.get('src') or poza.get('data-src') or poza.get('data-lazy-src')
            pret_float = curata_pret(pret.text)
            link_url = link['href']
            emag_id = extrage_emag_id(link_url)
            rezultate.append({
                "emag_id": emag_id,
                "nume": nume.text.strip(),
                "pret": pret_float,
                "pret_text": pret.text.strip(),
                "link": link_url,
                "poza": poza_url,
                "magazin": "eMAG"
            })
        return rezultate
    except Exception as e:
        print(f"Eroare scraper: {e}")
        return []

async def cauta_toate(query):
    return await cauta_emag(query)

async def scrape_produs(link):
    try:
        r = requests.get(link, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        nume = soup.select_one('h1.page-header')
        pret = soup.select_one('.product-new-price')
        poza = soup.select_one('img#main-image')
        if not pret:
            return None
        pret_float = curata_pret(pret.text)
        emag_id = extrage_emag_id(link)
        poza_url = None
        if poza:
            poza_url = poza.get('src') or poza.get('data-src')
        return {
            "emag_id": emag_id,
            "nume": nume.text.strip() if nume else "Produs",
            "pret": pret_float,
            "link": link,
            "poza": poza_url
        }
    except Exception as e:
        print(f"Eroare scrape produs: {e}")
        return None

def salveaza_rezultate(rezultate):
    produse_salvate = []
    for r in rezultate:
        if r.get('pret'):
            try:
                produs_id = salveaza_produs(
                    r['emag_id'], r['nume'],
                    r['link'], r.get('poza'), r['pret']
                )
                produse_salvate.append({**r, 'id': produs_id})
            except Exception as e:
                print(f"Eroare salvare: {e}")
    return produse_salvate
