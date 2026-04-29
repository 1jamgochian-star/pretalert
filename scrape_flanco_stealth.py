from playwright.sync_api import sync_playwright
import json
import time

def scrape_flanco_stealth(query):
    url = f"https://www.flanco.ro/catalogsearch/result/?q={query.replace(' ', '+')}"
    
    with sync_playwright() as p:
        # Lansăm browser-ul (headless=True pentru a economisi resurse pe Ipad5455)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print(f"🚀 Navighez către Flanco: {url}")
        
        try:
            # Navigăm și așteptăm încărcarea structurii de bază
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Așteptăm să apară produsele în listă
            print("⏳ Aștept încărcarea produselor și ofertelor...")
            page.wait_for_selector(".product-item", state="attached", timeout=15000)
            
            # Scroll scurt pentru a forța încărcarea prețurilor dinamice/lazy-load
            page.mouse.wheel(0, 1000)
            time.sleep(1) # Mică pauză pentru stabilizare
            
            produse = []
            items = page.query_selector_all(".product-item")
            print(f"🔎 Am găsit {len(items)} elemente. Extrag prețurile de ofertă...")
            
            for item in items:
                try:
                    # 1. Nume și Link
                    nume_elem = item.query_selector(".product-item-link")
                    if not nume_elem: continue
                    nume = nume_elem.inner_text().strip()
                    link = nume_elem.get_attribute("href")
                    
                    # 2. LOGICA DE PREȚ (Prioritate Oferta)
                    # Încercăm selectorul de preț special (cel roșu)
                    price_box = item.query_selector(".special-price [data-price-amount]")
                    
                    # Dacă nu există preț special, luăm prețul normal
                    if not price_box:
                        price_box = item.query_selector("[data-price-amount]")
                    
                    pret = price_box.get_attribute("data-price-amount") if price_box else "0"
                    
                    # 3. Imagine
                    img_elem = item.query_selector(".product-image-photo")
                    poza = img_elem.get_attribute("src") if img_elem else ""

                    produse.append({
                        "nume": nume,
                        "pret": pret,
                        "link": link,
                        "poza": poza
                    })
                except Exception:
                    continue
            
            browser.close()
            return produse

        except Exception as e:
            print(f"❌ Eroare în timpul navigării: {e}")
            if 'browser' in locals(): browser.close()
            return []

if __name__ == "__main__":
    # Testăm exact cu produsul din screenshot pentru a vedea scăderea de preț
    termen_cautare = "Samsung Galaxy A57" 
    rezultate = scrape_flanco_stealth(termen_cautare)
    
    if rezultate:
        fisier_iesire = "export_flanco.json"
        with open(fisier_iesire, "w", encoding="utf-8") as f:
            json.dump(rezultate, f, indent=4, ensure_ascii=False)
        print(f"✅ Gata! Am salvat {len(rezultate)} produse în {fisier_iesire}")
        print(f"💡 Verifică în JSON dacă prețul pentru A57 este acum cel de ofertă (~1974).")
    else:
        print("❌ Nu am extras niciun rezultat.")
