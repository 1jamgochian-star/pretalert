import requests
from bs4 import BeautifulSoup
import json

def scrape_flanco(query):
    # Folosim varianta de desktop pentru rezultate mai constante
    url = f"https://www.flanco.ro/catalogsearch/result/?q={query.replace(' ', '+')}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
        "DNT": "1"
    }

    print(f"🚀 Pornesc căutarea pe Flanco pentru: {query}...")
    
    try:
        # Folosim un timeout de 15 secunde ca să nu stea blocat dacă site-ul ne ignoră
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        print(f"✅ Răspuns primit (Cod: {response.status_code}). Parsez...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        produse = []
        # Selectorul pentru produsele din listă la Flanco
        items = soup.select('li.item.product-item')
        
        for item in items:
            try:
                # Nume și Link
                link_tag = item.select_one('a.product-item-link')
                nume = link_tag.get_text(strip=True)
                link = link_tag['href']
                
                # Preț - Flanco ține prețul în atributul data-price-amount de obicei
                price_box = item.select_one('[data-price-amount]')
                pret = price_box['data-price-amount'] if price_box else "0"
                
                # Imagine
                img_tag = item.select_one('img.product-image-photo')
                poza = img_tag['src'] if img_tag else ""
                
                produse.append({
                    "nume": nume,
                    "pret": pret,
                    "link": link,
                    "poza": poza
                })
            except Exception:
                continue

        return produse

    except Exception as e:
        print(f"❌ Eroare: {e}")
        return []

if __name__ == "__main__":
    rezultate = scrape_flanco("iphone 15")
    
    if rezultate:
        with open("export_flanco.json", "w", encoding="utf-8") as f:
            json.dump(rezultate, f, indent=4, ensure_ascii=False)
        print(f"🎉 Succes! Am găsit {len(rezultate)} produse și le-am salvat în export_flanco.json")
    else:
        print("🤷 Nu am găsit nimic. Verifică manual dacă link-ul de căutare returnează rezultate în browser.")
