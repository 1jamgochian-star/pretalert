import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import scrape_produs
from database import salveaza_produs, get_db
from mailer import trimite_alerta

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
                verifica_alerte(p['id'], rezultat['pret'], rezultat['nume'], p['link'])
        except Exception as e:
            logging.error(f"❌ Eroare {p['emag_id']}: {e}")

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
