import aiohttp
import asyncio
from bs4 import BeautifulSoup
from database import salveaza_produs
import re
import os
from dotenv import load_dotenv
load_dotenv()
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
print(f"SCRAPER_API_KEY loaded: {'OK' if SCRAPER_API_KEY else 'MISSING'}")

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

async def cauta_emag_pagina(query, pagina=1):
    if pagina == 1:
        emag_url = f"https://www.emag.ro/search/{query.replace(' ', '%20')}?ref=effective_search"
    else:
        emag_url = f"https://www.emag.ro/search/{query.replace(' ', '+')}/p{pagina}"
    url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={emag_url}&render=false"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
                html = await r.text()
                soup = BeautifulSoup(html, 'html.parser')
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
                        poza_url = (poza.get('src') or poza.get('data-src') or poza.get('data-lazy-src'))
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
        print(f"Eroare eMAG pagina {pagina}: {e}")
        return []

async def cauta_emag(query, pagini=1):
    toate_rezultatele = []
    for pagina in range(1, pagini + 1):
        rezultate = await cauta_emag_pagina(query, pagina)
        toate_rezultatele.extend(rezultate)
        if not rezultate:
            break
    return toate_rezultatele

async def cauta_emag_multe_pagini(query):
    return await cauta_emag(query, pagini=3)

async def cauta_flanco(query):
    flanco_url = f"https://www.flanco.ro/catalogsearch/result/?q={query.replace(' ', '+')}"
    url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={flanco_url}&render=false"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
                html = await r.text()
                soup = BeautifulSoup(html, 'html.parser')
                produse = soup.select('.product-item-info')
                rezultate = []
                for p in produse:
                    nume = p.select_one('.product-item-link')
                    pret = p.select_one('.price')
                    link = p.select_one('a.product-item-photo')
                    img = p.select_one('img')
                    if not nume or not pret or not link:
                        continue
                    pret_float = curata_pret(pret.text)
                    link_url = link['href']
                    poza_url = img['src'] if img else None
                    flanco_id = 'flanco_' + link_url.split('/')[-1].replace('.html', '')
                    rezultate.append({
                        "emag_id": flanco_id,
                        "nume": nume.text.strip(),
                        "pret": pret_float,
                        "pret_text": pret.text.strip(),
                        "link": link_url,
                        "poza": poza_url,
                        "magazin": "Flanco"
                    })
                return rezultate[:20]
    except Exception as e:
        print(f"Eroare Flanco: {e}")
        return []

async def scrape_produs(link):
    url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={link}&render=false"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
                html = await r.text()
                soup = BeautifulSoup(html, 'html.parser')
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

async def cauta_toate(query):
    rezultate_emag = await cauta_emag(query)
    rezultate_flanco = await cauta_flanco(query)
    return rezultate_emag + rezultate_flanco

def salveaza_rezultate(rezultate):
    produse_salvate = []
    print(f"Salvez {len(rezultate)} rezultate...")
    for r in rezultate:
        if r.get('pret'):
            try:
                produs_id = salveaza_produs(
                    r['emag_id'], r['nume'],
                    r['link'], r.get('poza'), r['pret']
                )
                produse_salvate.append({**r, 'id': produs_id})
            except Exception as e:
                print(f"Eroare salvare produs: {e}")
    print(f"Salvate cu succes: {len(produse_salvate)}")
    return produse_salvate
