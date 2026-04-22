import aiohttp
import asyncio
from bs4 import BeautifulSoup
from database import salveaza_produs
import re

import os
from dotenv import load_dotenv
load_dotenv()
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

def extrage_emag_id(link):
    match = re.search(r'/pd/([A-Z0-9]+)/', link)
    return match.group(1) if match else link.split('/')[-2]

def curata_pret(pret_text):
    pret_text = pret_text.replace('Lei', '').strip()
    pret_text = pret_text.replace('.', '').replace(',', '.')
    pret_text = re.sub(r'[^\d.]', '', pret_text)
    try:
        return float(pret_text)
    except:
        return None

async def cauta_emag(query):
    emag_url = f"https://www.emag.ro/search/{query.replace(' ', '+')}"
    url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={emag_url}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
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
                        poza_url = (poza.get('src') or 
                                   poza.get('data-src') or 
                                   poza.get('data-lazy-src'))
                    
                    pret_float = curata_pret(pret.text)
                    link_url = link['href']
                    emag_id = extrage_emag_id(link_url)
                    
                    rezultate.append({
                        "emag_id": emag_id,
                        "nume": nume.text.strip(),
                        "pret": pret_float,
                        "pret_text": pret.text.strip(),
                        "link": link_url,
                        "poza": poza_url
                    })
                
                return rezultate
    except Exception as e:
        print(f"Eroare scraper: {e}")
        return []

async def scrape_produs(link):
    url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={link}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
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
                    "nume": nume.text.strip() if nume else "Produs eMAG",
                    "pret": pret_float,
                    "link": link,
                    "poza": poza_url
                }
    except Exception as e:
        print(f"Eroare scrape produs: {e}")
        return None
async def cauta_altex(query):
    altex_url = f"https://altex.ro/cauta/{query.replace(' ', '-')}/"
    url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={altex_url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
                html = await r.text()
                soup = BeautifulSoup(html, 'html.parser')
                produse = soup.select('.Product')
                rezultate = []
                for p in produse:
                    nume = p.select_one('.Product-name')
                    pret = p.select_one('.Price-current')
                    link = p.select_one('a.Product-name')
                    if not nume or not pret or not link:
                        continue
                    poza = p.select_one('img')
                    poza_url = poza.get('src') or poza.get('data-src') if poza else None
                    pret_float = curata_pret(pret.text)
                    link_url = 'https://altex.ro' + link['href'] if link['href'].startswith('/') else link['href']
                    rezultate.append({
                        "emag_id": "altex_" + link_url.split('/')[-2],
                        "nume": nume.text.strip(),
                        "pret": pret_float,
                        "pret_text": pret.text.strip(),
                        "link": link_url,
                        "poza": poza_url,
                        "magazin": "Altex"
                    })
                return rezultate
    except Exception as e:
        print(f"Eroare Altex: {e}")
        return []

async def cauta_cel(query):
    cel_url = f"https://www.cel.ro/cauta/?q={query.replace(' ', '+')}"
    url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={cel_url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
                html = await r.text()
                soup = BeautifulSoup(html, 'html.parser')
                produse = soup.select('.product-card')
                rezultate = []
                for p in produse:
                    nume = p.select_one('.product-title')
                    pret = p.select_one('.price')
                    link = p.select_one('a')
                    if not nume or not pret or not link:
                        continue
                    poza = p.select_one('img')
                    poza_url = poza.get('src') or poza.get('data-src') if poza else None
                    pret_float = curata_pret(pret.text)
                    link_url = 'https://www.cel.ro' + link['href'] if link['href'].startswith('/') else link['href']
                    rezultate.append({
                        "emag_id": "cel_" + link_url.split('/')[-2],
                        "nume": nume.text.strip(),
                        "pret": pret_float,
                        "pret_text": pret.text.strip(),
                        "link": link_url,
                        "poza": poza_url,
                        "magazin": "Cel.ro"
                    })
                return rezultate
    except Exception as e:
        print(f"Eroare Cel.ro: {e}")
        return []
async def cauta_flanco(query):
    flanco_url = f"https://www.flanco.ro/catalogsearch/result/?q={query.replace(' ', '+')}"
    url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={flanco_url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
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
                    # curata poza URL (Flanco foloseste CDN transform)
                    if poza_url and 'flanco.ro/media' in poza_url:
                        poza_url = 'https://www.flanco.ro' + poza_url if poza_url.startswith('/') else poza_url
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
                return rezultate
    except Exception as e:
        print(f"Eroare Flanco: {e}")
        return []
async def cauta_toate(query):
    rezultate_emag, rezultate_altex, rezultate_cel, rezultate_flanco = await asyncio.gather(
        cauta_emag(query),
        cauta_altex(query),
        cauta_cel(query),
        cauta_flanco(query)
    )
    for r in rezultate_emag:
        r['magazin'] = 'eMAG'
    return rezultate_emag + rezultate_altex + rezultate_cel + rezultate_flanco

def salveaza_rezultate(rezultate):
    produse_salvate = []
    for r in rezultate:
        if r['pret']:
            produs_id = salveaza_produs(
                r['emag_id'], r['nume'], 
                r['link'], r['poza'], r['pret']
            )
            produse_salvate.append({**r, 'id': produs_id})
    return produse_salvate

if __name__ == "__main__":
    async def test():
        print("Caut produse...")
        rezultate = await cauta_emag("samsung galaxy watch ultra")
        print(f"Gasite: {len(rezultate)}")
        for r in rezultate[:3]:
            print(f"  {r['nume']} - {r['pret']} Lei")
    
    asyncio.run(test())
