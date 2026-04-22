import asyncio
import aiohttp
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
load_dotenv()
KEY = os.getenv('SCRAPER_API_KEY')

async def test():
    url = f'http://api.scraperapi.com?api_key={KEY}&render=true&url=https://altex.ro/cauta/samsung-galaxy-watch/'
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
            html = await r.text()
            soup = BeautifulSoup(html, 'html.parser')
            print('Titlu:', soup.title.text if soup.title else 'N/A')
            print(html[:3000])

asyncio.run(test())
