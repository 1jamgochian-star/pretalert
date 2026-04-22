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
        password TEXT NOT NULL,
        data_creare TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                  (produs_id, pret, datetime.now().isoformat()))

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

def get_db_sqlite():
    import sqlite3
    conn = sqlite3.connect('price_site.db')
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == "__main__":
    init_db()
