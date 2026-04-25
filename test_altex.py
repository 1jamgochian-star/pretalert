import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def test():
    url = 'https://www.flanco.ro/catalogsearch/result/?q=samsung+galaxy+watch+ultra'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as r:
            text = await r.text()
            print('Status:', r.status)
            print('Marime:', len(text))
            print('Captcha?', 'captcha' in text.lower())
            soup = BeautifulSoup(text, 'html.parser')
            produse = soup.select('.product-item-info')
            print('Produse gasite:', len(produse))
            for p in produse[:3]:
                nume = p.select_one('.product-item-link')
                pret = p.select_one('.price')
                if nume and pret:
                    print(nume.text.strip(), '-', pret.text.strip())

asyncio.run(test())
