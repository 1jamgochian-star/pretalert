import aiohttp
import asyncio
from bs4 import BeautifulSoup
from database import salveaza_produs
import re
import os
from dotenv import load_dotenv
load_dotenv()
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
CRAWLBASE_TOKEN = os.getenv("CRAWLBASE_TOKEN")
SCRAPINGBEE_TOKEN = os.getenv("SCRAPINGBEE_TOKEN")
print(f"SCRAPER_API_KEY  loaded: {'OK' if SCRAPER_API_KEY  else 'MISSING'}")
print(f"CRAWLBASE_TOKEN  loaded: {'OK' if CRAWLBASE_TOKEN  else 'MISSING'}")
print(f"SCRAPINGBEE_TOKEN loaded: {'OK' if SCRAPINGBEE_TOKEN else 'MISSING'}")

async def _fetch_via_scraperapi(session, target_url):
    url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={target_url}&render=false"
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
        if r.status != 200:
            raise Exception(f"HTTP {r.status}")
        return await r.text()

async def _fetch_via_crawlbase(session, target_url):
    url = f"https://api.crawlbase.com/?token={CRAWLBASE_TOKEN}&url={target_url}"
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
        pc_status = r.headers.get("pc_status", str(r.status))
        if r.status != 200 or pc_status not in ("200", "301", "302"):
            raise Exception(f"HTTP {r.status} pc_status={pc_status}")
        return await r.text()

async def _fetch_via_scrapingbee(session, target_url):
    url = f"https://app.scrapingbee.com/api/v1/?api_key={SCRAPINGBEE_TOKEN}&url={target_url}&render_js=false"
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
        if r.status != 200:
            raise Exception(f"HTTP {r.status}")
        return await r.text()

async def fetch_html(session, target_url, validator=None):
    """Încearcă ScraperAPI → Crawlbase → ScrapingBee.
    Trece la următorul dacă: excepție HTTP sau validator(html) returnează False."""
    scrapers = []
    if CRAWLBASE_TOKEN:
        scrapers.append(("Crawlbase", _fetch_via_crawlbase))
    if SCRAPINGBEE_TOKEN:
        scrapers.append(("ScrapingBee", _fetch_via_scrapingbee))
    if SCRAPER_API_KEY:
        scrapers.append(("ScraperAPI", _fetch_via_scraperapi))
    if not scrapers:
        raise Exception("Niciun scraper disponibil (SCRAPER_API_KEY, CRAWLBASE_TOKEN, SCRAPINGBEE_TOKEN lipsesc)")
    last_error = None
    for name, fetcher in scrapers:
        try:
            html = await fetcher(session, target_url)
            if validator and not validator(html):
                print(f"{name}: 0 produse găsite, încerc următorul scraper...")
                last_error = Exception("0 produse")
                continue
            return html
        except Exception as e:
            print(f"{name} eșuat ({e}), încerc următorul scraper...")
            last_error = e
    raise Exception(f"Toți scraper-ii au eșuat. Ultima eroare: {last_error}")

def _valid_emag(html):
    return bool(BeautifulSoup(html, 'html.parser').select('.card-item'))

def _valid_flanco(html):
    return bool(BeautifulSoup(html, 'html.parser').select('.product-item-info'))

def _valid_produs(html):
    return bool(BeautifulSoup(html, 'html.parser').select_one('.product-new-price'))

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
    try:
        async with aiohttp.ClientSession() as session:
            html = await fetch_html(session, emag_url, validator=_valid_emag)
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
async def cauta_emag(query):
    import requests as req
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ro-RO,ro;q=0.9',
    }
    emag_url = f"https://www.emag.ro/search/{query.replace(' ', '+')}"
    try:
        r = req.get(emag_url, headers=headers, timeout=30)
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

async def cauta_emag_multe_pagini(query):
    return await cauta_emag(query, pagini=3)

async def cauta_flanco(query):
    flanco_url = f"https://www.flanco.ro/catalogsearch/result/?q={query.replace(' ', '+')}"
    try:
        async with aiohttp.ClientSession() as session:
            html = await fetch_html(session, flanco_url, validator=_valid_flanco)
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
    try:
        async with aiohttp.ClientSession() as session:
            html = await fetch_html(session, link, validator=_valid_produs)
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
