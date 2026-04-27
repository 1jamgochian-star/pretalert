#!/usr/bin/env python3
"""
Importă produse dintr-un export WebScraper.io (CSV/JSON) în baza de date.
Detectează automat magazinul din URL și afișează raport per magazin.

Utilizare:
    python3 import_webscraper.py fisier.csv
    python3 import_webscraper.py fisier.json
    python3 import_webscraper.py fisier.csv --sursa "altex.ro"   # forțează sursa
"""

import sys
import os
import csv
import json
import re
import hashlib
import argparse
from collections import defaultdict
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import salveaza_produs

# ---------------------------------------------------------------------------
# Magazine cunoscute — domeniu → etichetă salvată în DB
# ---------------------------------------------------------------------------
MAGAZINE = {
    'emag.ro':          'emag.ro',
    'altex.ro':         'altex.ro',
    'flanco.ro':        'flanco.ro',
    'dedeman.ro':       'dedeman.ro',
    'cel.ro':           'cel.ro',
    'pcgarage.ro':      'pcgarage.ro',
    'mediagalaxy.ro':   'mediagalaxy.ro',
    'evomag.ro':        'evomag.ro',
    'vexio.ro':         'vexio.ro',
    'elefant.ro':       'elefant.ro',
    'okian.ro':         'okian.ro',
    'f64.ro':           'f64.ro',
    'quickmobile.ro':   'quickmobile.ro',
    'dc-shop.ro':       'dc-shop.ro',
    'digitaldepot.ro':  'digitaldepot.ro',
    'gomag.ro':         'gomag.ro',
}

# ---------------------------------------------------------------------------
# Alias-uri de coloane acceptate (case-insensitive, fără -/_/ )
# Ordinea contează: primul alias găsit câștigă.
# ---------------------------------------------------------------------------
ALIASES = {
    'nume': [
        'name', 'title', 'productname', 'producttitle',
        'denumire', 'produs', 'numeproduse', 'numeprodus',
        'titlu', 'item', 'itemname', 'nume',
    ],
    'pret': [
        'price', 'pret', 'pret href', 'price href',
        'prethref', 'pricehref', 'cost', 'valoare',
        'pretcurent', 'currentprice', 'saleprice', 'pretnou',
    ],
    'link': [
        'link', 'url', 'href', 'linkhref',
        'productlink', 'productlinkhref', 'producturl',
        'itemlink', 'itemurl', 'pageurl', 'pagina',
    ],
    'poza': [
        'image', 'img', 'poza', 'photo', 'picture',
        'imagesrc', 'imghref', 'thumbnail', 'imagehref',
        'productimage', 'productimagesrc', 'foto',
    ],
    'start_url': [
        'webscraperstarturl', 'starturl', 'webscraper start url',
    ],
}


# ---------------------------------------------------------------------------
# Detecție magazin
# ---------------------------------------------------------------------------

def detecteaza_magazin(url: str) -> str:
    """Extrage eticheta magazinului dintr-un URL de produs."""
    if not url:
        return ''
    try:
        domeniu = urlparse(url.strip()).netloc.lower()
        domeniu = re.sub(r'^www\.', '', domeniu)
    except Exception:
        return ''
    for cheie, eticheta in MAGAZINE.items():
        if cheie in domeniu:
            return eticheta
    return domeniu  # întoarce domeniul brut dacă nu e în lista noastră


# ---------------------------------------------------------------------------
# Mapare coloane
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    return re.sub(r'[-_\s]', '', s).lower()


def mapeaza_coloane(coloane: list[str]) -> dict[str, str]:
    """Întoarce {câmp_canonic: nume_coloană_real} pentru coloanele găsite."""
    norm_la_real = {_norm(c): c for c in coloane}
    mapare = {}
    for camp, aliasuri in ALIASES.items():
        for alias in aliasuri:
            if _norm(alias) in norm_la_real:
                mapare[camp] = norm_la_real[_norm(alias)]
                break
    return mapare


# ---------------------------------------------------------------------------
# Curățare preț
# ---------------------------------------------------------------------------

def curata_pret(valoare) -> float | None:
    if not valoare:
        return None
    s = re.sub(r'[^\d.,]', '', str(valoare).strip())
    if not s:
        return None

    if ',' in s and '.' in s:
        if s.rfind('.') > s.rfind(','):
            s = s.replace(',', '')           # 1,299.99  →  1299.99
        else:
            s = s.replace('.', '').replace(',', '.')  # 1.299,99  →  1299.99
    elif ',' in s:
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(',', '')           # 1,299  →  1299
        else:
            s = s.replace(',', '.')          # 699,99  →  699.99
    elif '.' in s:
        parts = s.split('.')
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace('.', '')           # 2.499  →  2499
        # altfel lasă ca float normal: 2.99

    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Citire fișier
# ---------------------------------------------------------------------------

def _detecteaza_format(cale: str) -> str:
    ext = os.path.splitext(cale)[1].lower()
    if ext in ('.csv',):
        return 'csv'
    if ext in ('.json',):
        return 'json'
    with open(cale, encoding='utf-8-sig') as f:
        primul_char = f.read(1).strip()
    return 'json' if primul_char in ('[', '{') else 'csv'


def citeste_fisier(cale: str) -> tuple[list[dict], list[str]]:
    fmt = _detecteaza_format(cale)
    if fmt == 'csv':
        with open(cale, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            randuri = list(reader)
            coloane = list(reader.fieldnames or [])
        return randuri, coloane
    else:
        with open(cale, encoding='utf-8') as f:
            date = json.load(f)
        if isinstance(date, dict):
            date = date.get('data', date.get('items', date.get('results', [])))
        if not isinstance(date, list) or not date:
            raise ValueError("JSON-ul trebuie să fie o listă de obiecte (sau {'data':[...]})")
        return date, list(date[0].keys())


# ---------------------------------------------------------------------------
# Import principal
# ---------------------------------------------------------------------------

def genereaza_id(link: str, sursa: str) -> str:
    return hashlib.md5(f"{sursa}::{link}".encode()).hexdigest()[:16]


def importa(cale_fisier: str, sursa_fortata: str | None = None) -> dict:
    """
    Importă fișierul și întoarce statistici per magazin:
    { 'emag.ro': {'ok': 5, 'sarit': 1, 'eroare': 0}, ... }
    """
    randuri, coloane = citeste_fisier(cale_fisier)
    mapare = mapeaza_coloane(coloane)

    campuri_lipsa = [c for c in ('nume', 'pret') if c not in mapare]
    if campuri_lipsa:
        print(f"\nEroare: coloane obligatorii negăsite: {campuri_lipsa}")
        print(f"Coloane din fișier: {coloane}")
        print("Redenumește coloanele în WebScraper.io sau vezi aliasurile acceptate.")
        sys.exit(1)

    fara_link    = 'link' not in mapare
    fara_poza    = 'poza' not in mapare
    fara_starturl = 'start_url' not in mapare

    if fara_link and fara_starturl:
        print("\nEroare: nicio coloană de URL găsită (link sau web_scraper_start_url).")
        print(f"Coloane din fișier: {coloane}")
        sys.exit(1)

    total = len(randuri)

    print(f"\nFișier : {cale_fisier}")
    print(f"Rânduri: {total}")
    print(f"Mapare : { {k: mapare[k] for k in ('nume','pret','link','start_url') if k in mapare} }")
    if fara_link:
        print("Info   : coloana link lipsă — se folosește web_scraper_start_url ca link de produs.")
    if fara_poza:
        print("Avertisment: coloana imagine negăsită — produse fără poză.")
    if sursa_fortata:
        print(f"Sursă  : {sursa_fortata} (forțată)\n")
    else:
        print("Sursă  : detectată automat din URL\n")

    stats: dict[str, dict] = defaultdict(lambda: {'ok': 0, 'sarit': 0, 'eroare': 0})
    total_ok = 0

    for i, rand in enumerate(randuri, 1):
        nume      = str(rand.get(mapare['nume'], '') or '').strip()
        link      = str(rand.get(mapare['link'], '') or '').strip() if not fara_link else ''
        start_url = str(rand.get(mapare['start_url'], '') or '').strip() if not fara_starturl else ''
        poza      = str(rand.get(mapare.get('poza', ''), '') or '').strip() if not fara_poza else ''
        pret_raw  = rand.get(mapare['pret'], '')

        # Fallback: folosim start_url când lipsește link-ul de produs
        if not link:
            link = start_url

        # Determină sursa
        if sursa_fortata:
            sursa = sursa_fortata
        else:
            sursa = detecteaza_magazin(link) or detecteaza_magazin(start_url) or 'necunoscut'

        if not nume or not link:
            print(f"  [{i:>4}/{total}] Sărit — câmp lipsă (nume={bool(nume)}, link={bool(link)})")
            stats[sursa]['sarit'] += 1
            continue

        pret = curata_pret(pret_raw)
        if pret is None:
            print(f"  [{i:>4}/{total}] Sărit — preț invalid {pret_raw!r:>12}  {nume[:45]}")
            stats[sursa]['sarit'] += 1
            continue

        emag_id = genereaza_id(link, sursa)

        try:
            salveaza_produs(emag_id, nume, link, poza or None, pret, sursa)
            total_ok += 1
            stats[sursa]['ok'] += 1
            print(f"  [{i:>4}/{total}] {sursa:15}  {pret:>10.2f} Lei  {nume[:50]}")
        except Exception as e:
            print(f"  [{i:>4}/{total}] Eroare DB: {e}  —  {nume[:45]}")
            stats[sursa]['eroare'] += 1

    return dict(stats)


def afiseaza_raport(stats: dict, cale: str):
    total_ok    = sum(v['ok']     for v in stats.values())
    total_sarit = sum(v['sarit']  for v in stats.values())
    total_err   = sum(v['eroare'] for v in stats.values())
    total       = total_ok + total_sarit + total_err

    linie = '─' * 56
    print(f"\n{linie}")
    print(f"  RAPORT IMPORT: {os.path.basename(cale)}")
    print(linie)
    print(f"  {'Magazin':<22} {'Import.':>7}  {'Sărite':>6}  {'Erori':>5}")
    print(linie)
    for magazin in sorted(stats):
        v = stats[magazin]
        print(f"  {magazin:<22} {v['ok']:>7}  {v['sarit']:>6}  {v['eroare']:>5}")
    print(linie)
    print(f"  {'TOTAL':<22} {total_ok:>7}  {total_sarit:>6}  {total_err:>5}  / {total}")
    print(linie)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Importă un export WebScraper.io în baza de date.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('fisier', help='Fișier CSV sau JSON exportat din WebScraper.io')
    parser.add_argument(
        '--sursa',
        default=None,
        help='Forțează sursa pentru toate produsele (implicit: detectat din URL)',
    )
    args = parser.parse_args()

    if not os.path.exists(args.fisier):
        print(f"Eroare: fișierul '{args.fisier}' nu există.")
        sys.exit(1)

    stats = importa(args.fisier, args.sursa)
    afiseaza_raport(stats, args.fisier)


if __name__ == '__main__':
    main()
