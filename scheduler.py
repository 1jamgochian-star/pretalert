import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import scrape_produs
from database import salveaza_produs, get_db
from mailer import trimite_alerta, trimite_raport_saptamanal

logging.basicConfig(level=logging.INFO)

# ── helpers ───────────────────────────────────────────────────────────────────

def verifica_alerte(produs_id, pret_curent, nume_produs, link_produs):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "SELECT id, email, pret_dorit FROM alerte WHERE produs_id = %s AND activa = 1 AND pret_dorit >= %s",
            (produs_id, pret_curent)
        )
        alerte = c.fetchall()
        conn.close()
        for alerta_id, email, pret_dorit in alerte:
            succes = trimite_alerta(email, nume_produs, pret_curent, pret_dorit, link_produs)
            if succes:
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE alerte SET activa = 0 WHERE id = %s", (alerta_id,))
                conn.commit()
                conn.close()
    except Exception as e:
        logging.error(f"Eroare trimitere alerta: {e}")

async def _scrape_si_salveaza(produse, verifica=False):
    for p in produse:
        try:
            rezultat = await scrape_produs(p['link'])
            if rezultat and rezultat['pret']:
                salveaza_produs(p['emag_id'], rezultat['nume'], p['link'], rezultat['poza'], rezultat['pret'])
                if verifica:
                    verifica_alerte(p['id'], rezultat['pret'], rezultat['nume'], p['link'])
        except Exception as e:
            logging.error(f"Eroare scrape {p['emag_id']}: {e}")

# ── job 1: vineri 02:00 — produse vizitate în ultimele 7 zile ─────────────────

async def _actualizeaza_vizitate():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT p.id, p.emag_id, p.link, p.pret_curent
        FROM produse p
        JOIN vizite v ON v.produs_id = p.id
        WHERE v.data >= NOW() - INTERVAL '7 days'
    """)
    rows = c.fetchall()
    conn.close()
    produse = [{'id': r[0], 'emag_id': r[1], 'link': r[2], 'pret_curent': r[3]} for r in rows]
    logging.info(f"Actualizare vizitate (7 zile): {len(produse)} produse...")
    await _scrape_si_salveaza(produse)

def job_vizitate():
    asyncio.run(_actualizeaza_vizitate())

# ── job 2: marți și vineri 08:00 — produse din urmariri ──────────────────────

async def _actualizeaza_urmariri():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT p.id, p.emag_id, p.link, p.pret_curent
        FROM produse p
        JOIN urmariri u ON u.produs_id = p.id
    """)
    rows = c.fetchall()
    conn.close()
    produse = [{'id': r[0], 'emag_id': r[1], 'link': r[2], 'pret_curent': r[3]} for r in rows]
    logging.info(f"Actualizare urmariri: {len(produse)} produse...")
    await _scrape_si_salveaza(produse, verifica=True)

def job_urmariri():
    asyncio.run(_actualizeaza_urmariri())

# ── job 3: zilnic 09:00 și 21:00 — alerte active ─────────────────────────────

async def _verifica_alerte_active():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT p.id, p.emag_id, p.link, p.pret_curent
        FROM produse p
        JOIN alerte a ON a.produs_id = p.id
        WHERE a.activa = 1
    """)
    rows = c.fetchall()
    conn.close()
    produse = [{'id': r[0], 'emag_id': r[1], 'link': r[2], 'pret_curent': r[3]} for r in rows]
    logging.info(f"Verificare alerte: {len(produse)} produse...")
    await _scrape_si_salveaza(produse, verifica=True)

def job_alerte():
    asyncio.run(_verifica_alerte_active())

# ── raport săptămânal: luni 10:00 ────────────────────────────────────────────

def trimite_rapoarte_saptamanale():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT
            u.id AS user_id,
            u.email,
            u.username,
            p.id AS produs_id,
            p.nume,
            p.link,
            p.pret_curent,
            ur.data AS data_urmarire,
            (
                SELECT ip.pret FROM istoric_preturi ip
                WHERE ip.produs_id = p.id
                ORDER BY ABS(EXTRACT(EPOCH FROM (ip.data - ur.data))) ASC
                LIMIT 1
            ) AS pret_initial
        FROM users u
        JOIN urmariri ur ON ur.user_id = u.id
        JOIN produse p ON p.id = ur.produs_id
        ORDER BY u.id, p.nume
    """)
    rows = c.fetchall()
    conn.close()

    useri = {}
    for row in rows:
        uid = row[0]
        if uid not in useri:
            useri[uid] = {'email': row[1], 'username': row[2], 'produse': []}
        useri[uid]['produse'].append({
            'produs_id':   row[3],
            'nume':        row[4],
            'link':        f"https://pretalert.ro/produs/{row[3]}",
            'pret_curent': row[6],
            'pret_initial': row[8],
        })

    logging.info(f"Raport saptamanal: {len(useri)} useri cu urmariri...")
    for date in useri.values():
        trimite_raport_saptamanal(date['email'], date['username'], date['produse'])

# ── start ─────────────────────────────────────────────────────────────────────

def start_scheduler():
    scheduler = BackgroundScheduler()

    # vineri 02:00 — produse vizitate în ultimele 7 zile
    scheduler.add_job(job_vizitate, 'cron', day_of_week='fri', hour=2, minute=0, id='actualizare_vizitate')

    # marți și vineri 08:00 — urmariri (favorite)
    scheduler.add_job(job_urmariri, 'cron', day_of_week='tue,fri', hour=8, minute=0, id='actualizare_urmariri')

    # zilnic 09:00 și 21:00 — alerte active
    scheduler.add_job(job_alerte, 'cron', hour='9,21', minute=0, id='verificare_alerte')

    # luni 10:00 — raport săptămânal
    scheduler.add_job(trimite_rapoarte_saptamanale, 'cron', day_of_week='mon', hour=10, minute=0, id='raport_saptamanal')

    scheduler.start()
    logging.info(
        "Scheduler pornit:\n"
        "  - vizitate:  vineri 02:00\n"
        "  - urmariri:  marti + vineri 08:00\n"
        "  - alerte:    zilnic 09:00 si 21:00\n"
        "  - raport:    luni 10:00"
    )
    return scheduler
