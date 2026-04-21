import sqlite3
from datetime import datetime

DB_PATH = "price_site.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS produse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emag_id TEXT UNIQUE,
        nume TEXT NOT NULL,
        link TEXT NOT NULL,
        poza TEXT,
        pret_curent REAL,
        data_adaugare TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        username TEXT,
        password_hash TEXT,
        google_id TEXT,
        facebook_id TEXT,
        avatar TEXT,
        data_creare TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS istoric_preturi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produs_id INTEGER,
        pret REAL,
        data TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produs_id) REFERENCES produse(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS alerte (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produs_id INTEGER,
        email TEXT NOT NULL,
        pret_dorit REAL NOT NULL,
        activa INTEGER DEFAULT 1,
        data_creare TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produs_id) REFERENCES produse(id)
    )''')

    conn.commit()
    conn.close()
    print("✅ Baza de date initializata!")

def salveaza_produs(emag_id, nume, link, poza, pret):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('''INSERT OR IGNORE INTO produse
                     (emag_id, nume, link, poza, pret_curent)
                     VALUES (?, ?, ?, ?, ?)''',
                  (emag_id, nume, link, poza, pret))
        c.execute('''UPDATE produse SET pret_curent=?, poza=?
                     WHERE emag_id=?''', (pret, poza, emag_id))
        c.execute('SELECT id FROM produse WHERE emag_id=?', (emag_id,))
        produs_id = c.fetchone()[0]
        c.execute('''INSERT INTO istoric_preturi (produs_id, pret, data)
                     VALUES (?, ?, ?)''',
                  (produs_id, pret, datetime.now().isoformat()))
        conn.commit()
        return produs_id
    finally:
        conn.close()

def get_produs(produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM produse WHERE id=?', (produs_id,))
    produs = c.fetchone()
    conn.close()
    return produs

def get_istoric(produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT pret, data FROM istoric_preturi
                 WHERE produs_id=? ORDER BY data ASC''', (produs_id,))
    istoric = c.fetchall()
    conn.close()
    return istoric

def salveaza_alerta(produs_id, email, pret_dorit):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO alerte (produs_id, email, pret_dorit)
                 VALUES (?, ?, ?)''', (produs_id, email, pret_dorit))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
