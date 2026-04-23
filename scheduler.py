import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import scrape_produs
from database import salveaza_produs, get_db

logging.basicConfig(level=logging.INFO)

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
        except Exception as e:
            logging.error(f"❌ Eroare {p['emag_id']}: {e}")

def job_actualizare():
    asyncio.run(actualizeaza_toate_preturile())

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        job_actualizare,
        'interval',
        hours=12,
        id='actualizare_preturi'
    )
    scheduler.start()
    logging.info("✅ Scheduler pornit - actualizare la fiecare 12 ore")
    return scheduler
