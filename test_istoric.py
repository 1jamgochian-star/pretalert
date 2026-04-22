import aiohttp
import asyncio
from bs4 import BeautifulSoup
import urllib.parse

SCRAPER_API_KEY = "828c1cf21d9cd3260fa48783f96bd2c6"

async def test_istoric():
    query = "samsung galaxy watch ultra"
    encoded = urllib.parse.quote(query)
    
    # Cu JavaScript rendering activat
    emag_url = f"https://www.istoric-preturi.info/search?q={encoded}"
    api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={emag_url}&render=true&wait=3000"
    
    print("Asteapta ~30 secunde pentru JS rendering...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=120)) as r:
            html = await r.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            print("Status:", r.status)
            print("Marime HTML:", len(html))
            
            print("\n=== LINK-URI PRODUSE ===")
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.text.strip()
                if text and len(text) > 10:
                    print(f"{text[:70]} -> {href}")
            
            print("\n=== TEXT ===")
            print(soup.get_text()[:2000])

asyncio.run(test_istoric())
