from playwright.sync_api import sync_playwright
import json

def scrape_flanco_stealth(query):
    url = f"https://www.flanco.ro/catalogsearch/result/?q={query.replace(' ', '+')}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Adăugăm un context mai realist
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print(f"🚀 Navighez către Flanco...")
        page.goto(url, wait_until="domcontentloaded") # Nu mai așteptăm networkidle (e prea lent)
        
        # Așteptăm doar să existe în DOM, nu neapărat să fie "visible" (evită TimeoutError)
        print("⏳ Aștept produsele...")
        page.wait_for_selector(".product-item", state="attached", timeout=15000)
        
        # Dăm un mic scroll ca să se încarce eventualele elemente de lazy-load
        page.mouse.wheel(0, 500)
        
        produse = []
        items = page.query_selector_all(".product-item")
        print(f"🔎 Am găsit {len(items)} elemente. Extrag datele...")
        
        for item in items:
            try:
                nume_elem = item.query_selector(".product-item-link")
                if not nume_elem: continue
                
                nume = nume_elem.inner_text().strip()
                link = nume_elem.get_attribute("href")
                
                # Căutăm prețul în atributul data-price-amount
                price_elem = item.query_selector("[data-price-amount]")
                pret = price_elem.get_attribute("data-price-amount") if price_elem else "0"
                
                # Imaginea (uneori e în 'data-src' sau 'src')
                img_elem = item.query_selector(".product-image-photo")
                poza = img_elem.get_attribute("src") if img_elem else ""

                produse.append({
                    "nume": nume,
                    "pret": pret,
                    "link": link,
                    "poza": poza
                })
            except Exception as e:
                continue
        
        browser.close()
        return produse

if __name__ == "__main__":
    rezultate = scrape_flanco_stealth("iphone 15")
    if rezultate:
        with open("export_flanco.json", "w", encoding="utf-8") as f:
            json.dump(rezultate, f, indent=4, ensure_ascii=False)
        print(f"✅ Gata! Am extras {len(rezultate)} produse în export_flanco.json")
    else:
        print("❌ Nu am reușit să extragem datele.")
