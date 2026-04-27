"""
Migrare one-shot: actualizează linkurile Altex fără /cpd/SKU/ la formatul corect.
Rulează: python3 migrate_altex_links.py
"""
import asyncio
import psycopg2
import psycopg2.extras
from urllib.parse import quote
from curl_cffi.requests import AsyncSession as CurlSession
from database import get_db

CONCURENTA = 10  # requesturi Fenrir simultane


async def get_sku(session, url_key: str) -> str | None:
    api = f"https://fenrir.altex.ro/v2/catalog/search/{quote(url_key, safe='')}?size=1"
    try:
        r = await session.get(api, impersonate="chrome110", timeout=20)
        products = r.json().get('products') or []
        if products:
            return (products[0].get('sku') or '').strip() or None
    except Exception as e:
        print(f"  Eroare Fenrir pentru '{url_key[:40]}': {e}")
    return None


async def main():
    # 1. Ia toate produsele Altex fără /cpd/ în link
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("""
        SELECT id, link FROM produse
        WHERE sursa = 'Altex' AND link NOT LIKE '%/cpd/%'
    """)
    produse = c.fetchall()
    conn.close()
    print(f"Produse de actualizat: {len(produse)}")

    sem = asyncio.Semaphore(CONCURENTA)
    actualizate = 0
    negasite = 0

    async def proceseaza(session, produs):
        nonlocal actualizate, negasite
        pid = produs['id']
        link = produs['link']

        # Extrage url_key: tot ce e după altex.ro/
        url_key = link.replace('https://altex.ro/', '').rstrip('/')

        async with sem:
            sku = await get_sku(session, url_key)

        if not sku:
            print(f"  [SKIP] id={pid} — SKU negăsit pentru '{url_key[:50]}'")
            negasite += 1
            return

        nou_link = f"https://altex.ro/{url_key}/cpd/{sku}/"

        conn2 = get_db()
        try:
            c2 = conn2.cursor()
            c2.execute(
                "UPDATE produse SET link = %s WHERE id = %s",
                (nou_link, pid)
            )
            conn2.commit()
            actualizate += 1
            print(f"  [OK] id={pid} | {url_key[:45]} → /cpd/{sku}/")
        except Exception as e:
            conn2.rollback()
            print(f"  [ERR] id={pid}: {e}")
        finally:
            conn2.close()

    async with CurlSession() as session:
        await asyncio.gather(*[proceseaza(session, p) for p in produse])

    print(f"\nRezultat: {actualizate} actualizate, {negasite} SKU negăsite")


if __name__ == '__main__':
    asyncio.run(main())
