import aiohttp
import asyncio
from bs4 import BeautifulSoup

SCRAPER_API_KEY = "828c1cf21d9cd3260fa48783f96bd2c6"

async def test():
    emag_url = "https://www.emag.ro/search/samsung+galaxy+watch+ultra"
    url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={emag_url}"
    
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
                poza = p.select_one('img')
poza_url = None
if poza:
    poza_url = poza.get('src') or poza.get('data-src') or poza.get('data-lazy-src')
                
                # Sari peste carduri fara date complete
                if not nume or not pret or not link:
                    continue
                
                rezultate.append({
                    "nume": nume.text.strip(),
                    "pret": pret.text.strip(),
                    "link": link['href'],
                    "poza": poza['src'] if poza else None
                })
            
            print(f"Produse valide: {len(rezultate)}")
            for r in rezultate[:5]:
                print("---")
                print("Nume:", r['nume'])
                print("Pret:", r['pret'])
                print("Link:", r['link'])
                print("Poza:", r['poza'])

asyncio.run(test())
