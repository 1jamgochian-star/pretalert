import asyncio
import time
from scraper import cauta_emag_pagina
from database import salveaza_produs

CATEGORII = [
    ("Telefoane mobile",    "telefon mobil"),
    ("Laptopuri",           "laptop"),
    ("Televizoare",         "televizor"),
    ("Tablete",             "tableta"),
    ("Smartwatch-uri",      "smartwatch"),
    ("Căști audio",         "casti audio"),
    ("Frigidere",           "frigider"),
    ("Mașini de spălat",    "masina de spalat"),
    ("Aspiratoare",         "aspirator"),
    ("Camere foto",         "camera foto"),
    ("Console gaming",      "consola gaming"),
    ("Monitoare",           "monitor"),
]

PAGINI_PER_CATEGORIE = 5
PAUZA_INTRE_PAGINI = 2   # secunde între cereri ScraperAPI


def salveaza_rezultate_batch(rezultate, categorie):
    salvate = 0
    for r in rezultate:
        if not r.get('pret'):
            continue
        try:
            salveaza_produs(r['emag_id'], r['nume'], r['link'], r.get('poza'), r['pret'])
            salvate += 1
        except Exception as e:
            print(f"    [!] Eroare salvare '{r.get('nume', '?')[:40]}': {e}")
    return salvate


async def scrape_categorie(nume_categorie, query):
    print(f"\n{'='*55}")
    print(f"  {nume_categorie}  ({query})")
    print(f"{'='*55}")
    total_salvate = 0

    for pagina in range(1, PAGINI_PER_CATEGORIE + 1):
        print(f"  Pagina {pagina}/{PAGINI_PER_CATEGORIE}...", end=" ", flush=True)
        try:
            rezultate = await cauta_emag_pagina(query, pagina)
        except Exception as e:
            print(f"EROARE: {e}")
            continue

        if not rezultate:
            print("0 produse (posibil ultima pagina)")
            break

        salvate = salveaza_rezultate_batch(rezultate, nume_categorie)
        total_salvate += salvate
        print(f"{len(rezultate)} găsite, {salvate} salvate (total: {total_salvate})")

        if pagina < PAGINI_PER_CATEGORIE:
            await asyncio.sleep(PAUZA_INTRE_PAGINI)

    return total_salvate


async def main():
    start = time.time()
    print(f"Populate DB — {len(CATEGORII)} categorii x {PAGINI_PER_CATEGORIE} pagini")
    print(f"Estimat: ~{len(CATEGORII) * PAGINI_PER_CATEGORIE * 60 // 60} minute\n")

    grand_total = 0
    for nume_categorie, query in CATEGORII:
        total = await scrape_categorie(nume_categorie, query)
        grand_total += total
        print(f"  => {nume_categorie}: {total} produse salvate")
        await asyncio.sleep(PAUZA_INTRE_PAGINI)

    elapsed = int(time.time() - start)
    print(f"\n{'='*55}")
    print(f"  GATA! {grand_total} produse salvate în {elapsed // 60}m {elapsed % 60}s")
    print(f"{'='*55}")


if __name__ == "__main__":
    asyncio.run(main())
