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
