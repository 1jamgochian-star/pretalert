import psycopg2
import psycopg2.extras
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS produse (
        id SERIAL PRIMARY KEY,
        emag_id TEXT UNIQUE,
        nume TEXT NOT NULL,
        link TEXT NOT NULL,
        poza TEXT,
        pret_curent REAL,
        data_adaugare TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS istoric_preturi (
        id SERIAL PRIMARY KEY,
        produs_id INTEGER,
        pret REAL,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produs_id) REFERENCES produse(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS alerte (
        id SERIAL PRIMARY KEY,
        produs_id INTEGER,
        email TEXT NOT NULL,
        pret_dorit REAL NOT NULL,
        activa INTEGER DEFAULT 1,
        data_creare TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produs_id) REFERENCES produse(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT,
        avatar TEXT,
        google_id TEXT,
        facebook_id TEXT,
        data_creare TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS urmariri (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        produs_id INTEGER,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, produs_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS vizite (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        produs_id INTEGER,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    print("✅ Baza de date PostgreSQL initializata!")

def salveaza_produs(emag_id, nume, link, poza, pret):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO produse (emag_id, nume, link, poza, pret_curent)
                     VALUES (%s, %s, %s, %s, %s)
                     ON CONFLICT (emag_id) DO UPDATE
                     SET pret_curent=%s, poza=%s''',
                  (emag_id, nume, link, poza, pret, pret, poza))
        c.execute('SELECT id FROM produse WHERE emag_id=%s', (emag_id,))
        produs_id = c.fetchone()[0]
        c.execute('''INSERT INTO istoric_preturi (produs_id, pret, data)
                     VALUES (%s, %s, %s)''',
                  (produs_id, pret, datetime.now()))
        conn.commit()
        return produs_id
    finally:
        conn.close()

def get_produs(produs_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute('SELECT * FROM produse WHERE id=%s', (produs_id,))
    produs = c.fetchone()
    conn.close()
    return produs

def get_istoric(produs_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute('''SELECT pret, data FROM istoric_preturi
                 WHERE produs_id=%s ORDER BY data ASC''', (produs_id,))
    istoric = c.fetchall()
    conn.close()
    return istoric

def salveaza_alerta(produs_id, email, pret_dorit):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO alerte (produs_id, email, pret_dorit)
                 VALUES (%s, %s, %s)''', (produs_id, email, pret_dorit))
    conn.commit()
    conn.close()

def get_alerte_user(email):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute('''SELECT a.*, p.nume, p.pret_curent, p.link
                 FROM alerte a JOIN produse p ON a.produs_id = p.id
                 WHERE a.email=%s AND a.activa=1''', (email,))
    alerte = c.fetchall()
    conn.close()
    return alerte

def sterge_alerta(alerta_id, email):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM alerte WHERE id=%s AND email=%s', (alerta_id, email))
    conn.commit()
    conn.close()

def schimba_parola(user_id, pw_hash):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET password=%s WHERE id=%s', (pw_hash, user_id))
    conn.commit()
    conn.close()

def schimba_username(user_id, username):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET username=%s WHERE id=%s', (username, user_id))
    conn.commit()
    conn.close()

def urmareste_produs(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO urmariri (user_id, produs_id) VALUES (%s, %s) ON CONFLICT DO NOTHING',
              (user_id, produs_id))
    conn.commit()
    conn.close()

def sterge_urmarire(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM urmariri WHERE user_id=%s AND produs_id=%s', (user_id, produs_id))
    conn.commit()
    conn.close()

def get_produse_urmarite(user_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute('''SELECT p.* FROM produse p
                 JOIN urmariri u ON p.id = u.produs_id
                 WHERE u.user_id=%s
                 ORDER BY u.data DESC''', (user_id,))
    produse = c.fetchall()
    conn.close()
    return produse

def este_urmarit(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM urmariri WHERE user_id=%s AND produs_id=%s', (user_id, produs_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def salveaza_vizita(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO vizite (user_id, produs_id) VALUES (%s, %s)', (user_id, produs_id))
    conn.commit()
    conn.close()

def get_istoric_vizite(user_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute('''SELECT p.*, v.data as data_vizita FROM produse p
                 JOIN vizite v ON p.id = v.produs_id
                 WHERE v.user_id=%s
                 ORDER BY v.data DESC LIMIT 20''', (user_id,))
    vizite = c.fetchall()
    conn.close()
    return vizite

if __name__ == "__main__":
    init_db()
