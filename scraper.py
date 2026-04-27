import os
import asyncio
import hashlib
import aiohttp
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession as CurlSession
from database import salveaza_produs
from urllib.parse import quote
import re

SCRAPER_API_KEY = os.getenv('SCRAPER_API_KEY', '')


def _scraper_url(target_url, render=False):
    params = f"api_key={SCRAPER_API_KEY}&url={quote(target_url, safe='')}"
    if render:
        params += "&render=true"
    return f"http://api.scraperapi.com?{params}"


def _slug_id(prefix, url):
    return prefix + '_' + hashlib.md5(url.encode()).hexdigest()[:12]


def extrage_emag_id(link):
    match = re.search(r'/pd/([A-Z0-9]+)/', link)
    return match.group(1) if match else link.split('/')[-2]


def curata_pret(pret_text):
    pret_text = pret_text.replace('Lei', '').replace('lei', '').replace('RON', '').strip()
    pret_text = pret_text.replace('.', '').replace(',', '.')
    pret_text = re.sub(r'[^\d.]', '', pret_text)
    try:
        return float(pret_text)
    except Exception:
        return None


async def _fetch(session, url, render=False, timeout=45):
    api_url = _scraper_url(url, render=render)
    try:
        async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            return await r.text()
    except Exception as e:
        print(f"Fetch eroare {url[:60]}: {e}")
        return ''


# ── Scrapers per magazin ─────────────────────────────────────────────────────

async def _cauta_emag(session, query, pagina=1):
    if pagina == 1:
        url = f"https://www.emag.ro/search/{query.replace(' ', '+')}"
    else:
        url = f"https://www.emag.ro/search/{query.replace(' ', '+')}/p{pagina}/c"
    html = await _fetch(session, url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    rezultate = []
    for p in soup.select('.card-item'):
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
        rezultate.append({
            'emag_id': extrage_emag_id(link_url),
            'nume': nume.text.strip(),
            'pret': pret_float,
            'link': link_url,
            'poza': poza_url,
            'sursa': 'eMAG',
        })
    print(f"eMAG: {len(rezultate)} produse")
    return rezultate


async def cauta_altex(query):
    """Caută pe Altex via API-ul oficial Fenrir (fără ScraperAPI)."""
    api_url = (
        f"https://fenrir.altex.ro/v2/catalog/search/{quote(query, safe='')}?size=48"
    )
    try:
        async with CurlSession() as session:
            r = await session.get(api_url, impersonate="chrome110", timeout=30)
            data = r.json()
    except Exception as e:
        print(f"Altex API eroare: {e}")
        return []

    hits = (
        data.get('hits')
        or data.get('products')
        or (data.get('data') or {}).get('hits')
        or []
    )

    rezultate = []
    for p in hits:
        nume = (p.get('name') or '').strip()
        url_key = p.get('url_key', '')

        # preț — structură RON nested
        pret = None
        price_data = p.get('price', {})
        if isinstance(price_data, dict):
            ron = price_data.get('RON') or price_data.get('ron') or {}
            if isinstance(ron, dict):
                pret = ron.get('default') or ron.get('final') or ron.get('min')
            elif isinstance(ron, (int, float)):
                pret = float(ron)
        elif isinstance(price_data, (int, float)):
            pret = float(price_data)

        # imagine — path relativ /media/catalog/product/a/b/xxx.jpg
        raw_img = p.get('image') or p.get('thumbnail') or p.get('small_image') or ''
        if raw_img:
            img_path = raw_img.lstrip('/')          # "media/catalog/product/a/b/xxx.jpg"
            if img_path.startswith('media/catalog/product/'):
                img_path = img_path[len('media/catalog/product/'):]
            poza_url = f"https://lcdn.altex.ro/resize/media/catalog/product/{img_path}"
        else:
            poza_url = None

        if not nume or not url_key or not pret:
            continue

        link = f"https://altex.ro/{url_key}"
        rezultate.append({
            'emag_id': _slug_id('altex', link),
            'nume': nume,
            'pret': float(pret),
            'link': link,
            'poza': poza_url,
            'sursa': 'Altex',
        })

    print(f"Altex API: {len(rezultate)} produse")
    return rezultate


async def _cauta_flanco(session, query):
    url = f"https://www.flanco.ro/catalogsearch/result/?q={quote(query, safe='')}"
    html = await _fetch(session, url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    rezultate = []
    for p in soup.select('li.product-item'):
        link_el = p.select_one('a.product-item-link')
        pret_el = p.select_one('span.price')
        if not link_el or not pret_el:
            continue
        link_url = link_el.get('href', '')
        pret_float = curata_pret(pret_el.get_text())
        poza_el = p.select_one('img.product-image-photo, img')
        poza_url = poza_el.get('src') if poza_el else None
        if not link_url or not pret_float:
            continue
        rezultate.append({
            'emag_id': _slug_id('flanco', link_url),
            'nume': link_el.text.strip(),
            'pret': pret_float,
            'link': link_url,
            'poza': poza_url,
            'sursa': 'Flanco',
        })
    print(f"Flanco: {len(rezultate)} produse")
    return rezultate


async def _cauta_cel(session, query):
    url = f"https://www.cel.ro/cauta/?search_term={quote(query, safe='')}"
    html = await _fetch(session, url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    rezultate = []
    for p in soup.select('.product-item, .produs-item, .prd_box, [class*="product-item"]'):
        link_el = (
            p.select_one('a[href*="/produse/"]') or
            p.select_one('h2 a, h3 a, .product-name a, .title a')
        )
        pret_el = p.select_one('.price, .pret, .Price, [class*="price"], [class*="pret"]')
        if not link_el or not pret_el:
            continue
        link_url = link_el.get('href', '')
        if link_url and not link_url.startswith('http'):
            link_url = 'https://www.cel.ro' + link_url
        pret_float = curata_pret(pret_el.get_text())
        poza_el = p.select_one('img')
        poza_url = poza_el.get('src') if poza_el else None
        if not link_url or not pret_float:
            continue
        rezultate.append({
            'emag_id': _slug_id('cel', link_url),
            'nume': link_el.text.strip(),
            'pret': pret_float,
            'link': link_url,
            'poza': poza_url,
            'sursa': 'CEL',
        })
    print(f"CEL: {len(rezultate)} produse")
    return rezultate


async def _cauta_pcgarage(session, query):
    url = f"https://www.pcgarage.ro/cauta/{quote(query, safe='')}/"
    html = await _fetch(session, url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    rezultate = []
    for p in soup.select('.product-layout, .product-item'):
        link_el = (
            p.select_one('.caption h4 a') or
            p.select_one('h4 a, .product-title a')
        )
        pret_el = p.select_one('.price-new, .price, [class*="price"]')
        if not link_el or not pret_el:
            continue
        link_url = link_el.get('href', '')
        if link_url and not link_url.startswith('http'):
            link_url = 'https://www.pcgarage.ro' + link_url
        pret_float = curata_pret(pret_el.get_text())
        poza_el = p.select_one('.image img, img')
        poza_url = poza_el.get('src') or poza_el.get('data-src') if poza_el else None
        if not link_url or not pret_float:
            continue
        rezultate.append({
            'emag_id': _slug_id('pcg', link_url),
            'nume': link_el.text.strip(),
            'pret': pret_float,
            'link': link_url,
            'poza': poza_url,
            'sursa': 'PC Garage',
        })
    print(f"PC Garage: {len(rezultate)} produse")
    return rezultate


# ── API public ───────────────────────────────────────────────────────────────

async def cauta_emag(query, pagina=1):
    """Compatibilitate cu app.py — caută doar pe eMAG."""
    async with aiohttp.ClientSession() as session:
        return await _cauta_emag(session, query, pagina)


async def cauta_toate(query):
    """Caută pe toate magazinele în paralel cu asyncio.gather()."""
    async with aiohttp.ClientSession() as session:
        rezultate_list = await asyncio.gather(
            _cauta_emag(session, query),
            cauta_altex(query),          # curl_cffi — sesiune proprie
            _cauta_flanco(session, query),
            _cauta_cel(session, query),
            _cauta_pcgarage(session, query),
            return_exceptions=True,
        )
    combined = []
    for r in rezultate_list:
        if isinstance(r, list):
            combined.extend(r)
        elif isinstance(r, Exception):
            print(f"Eroare magazin: {r}")
    print(f"Total toate magazinele: {len(combined)} produse")
    return combined


async def scrape_produs(link):
    try:
        async with aiohttp.ClientSession() as session:
            html = await _fetch(session, link)
        if not html:
            return None
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
            'emag_id': emag_id,
            'nume': nume.text.strip() if nume else 'Produs',
            'pret': pret_float,
            'link': link,
            'poza': poza_url,
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
                    r['link'], r.get('poza'), r['pret'],
                    r.get('sursa', 'eMAG'),
                )
                produse_salvate.append({**r, 'id': produs_id})
            except Exception as e:
                print(f"Eroare salvare: {e}")
    return produse_salvate
