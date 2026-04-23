import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import scrape_produs, cauta_emag, cauta_emag_multe_pagini
from database import salveaza_produs, get_db
from mailer import trimite_alerta

logging.basicConfig(level=logging.INFO)

CATEGORII_POPULARE = [
    "samsung galaxy",
    "iphone",
    "laptop",
    "televizor",
    "tableta",
    "airpods",
    "smartwatch",
    "aspirator",
    "frigider",
    "masina de spalat",
    "playstation",
    "xbox",
    "monitor",
    "tastatura",
    "mouse",
    "router",
    "camera foto",
    "capsule cafea",
    "robot aspirator",
    "apple watch"
]

async def actualizeaza_toate_preturile():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, emag_id, link, pret_curent FROM produse')
    rows = c.fetchall()
    conn.close()
    produse = [{'id': r[0], 'emag_id': r[1], 'link': r[2], 'pret_curent': r[3]} for r in rows]
    logging.info(f"Actualizez {len(produse)} produse...")
    for p in produse:
        try:
            rezultat = await scrape_produs(p['link'])
            if rezultat and rezultat['pret']:
                salveaza_produs(
                    p['emag_id'],
                    rezultat['nume'],
                    p['link'],
                    rezultat['poza'],
                    rezultat['pret']
                )
                logging.info(f"✅ {p['emag_id']}: {rezultat['pret']} Lei")
                verifica_alerte(p['id'], rezultat['pret'], rezultat['nume'], p['link'])
        except Exception as e:
            logging.error(f"❌ Eroare {p['emag_id']}: {e}")

async def preincarca_categorii():
    logging.info("🔄 Pre-încărcare categorii populare...")
    for categorie in CATEGORII_POPULARE:
        try:
            from scraper import scrape_produs, cauta_emag, cauta_emag_multe_pagini
            for r in rezultate[:10]:
                if r.get('pret'):
                    try:
                        salveaza_produs(
                            r['emag_id'], r['nume'],
                            r['link'], r.get('poza'), r['pret']
                        )
                    except Exception as e:
                        logging.error(f"❌ Eroare salvare {r['emag_id']}: {e}")
            logging.info(f"✅ Categorie '{categorie}': {len(rezultate)} produse")
        except Exception as e:
            logging.error(f"❌ Eroare categorie '{categorie}': {e}")

def verifica_alerte(produs_id, pret_curent, nume_produs, link_produs):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT id, email, pret_dorit FROM alerte
            WHERE produs_id = %s AND activa = 1 AND pret_dorit >= %s
        """, (produs_id, pret_curent))
        alerte = c.fetchall()
        conn.close()
        for alerta in alerte:
            alerta_id, email, pret_dorit = alerta
            succes = trimite_alerta(email, nume_produs, pret_curent, pret_dorit, link_produs)
            if succes:
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE alerte SET activa = 0 WHERE id = %s", (alerta_id,))
                conn.commit()
                conn.close()
                logging.info(f"✅ Alertă trimisă la {email}")
    except Exception as e:
        logging.error(f"❌ Eroare verificare alerte: {e}")

def job_actualizare():
    asyncio.run(actualizeaza_toate_preturile())

def job_preincarca():
    asyncio.run(preincarca_categorii())

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        job_actualizare,
        'interval',
        hours=12,
        id='actualizare_preturi'
    )
    scheduler.add_job(
        job_preincarca,
        'cron',
        hour=3,
        minute=0,
        id='preincarca_categorii'
    )
    scheduler.start()
    logging.info("✅ Scheduler pornit - actualizare la fiecare 12 ore")

    # Porneste pre-incarcare imediat la primul start
    import threading
    t = threading.Thread(target=job_preincarca)
    t.daemon = True
    t.start()

    return scheduler
