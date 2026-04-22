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

    c.execute('''CREATE TABLE IF NOT EXISTS produse_urmarite (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        produs_id INTEGER,
        data_adaugare TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, produs_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (produs_id) REFERENCES produse(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS istoric_vizite (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        produs_id INTEGER,
        data_vizita TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
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

def urmareste_produs(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO produse_urmarite (user_id, produs_id) VALUES (?,?)',
              (user_id, produs_id))
    conn.commit()
    conn.close()

def sterge_urmarire(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM produse_urmarite WHERE user_id=? AND produs_id=?',
              (user_id, produs_id))
    conn.commit()
    conn.close()

def get_produse_urmarite(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT p.*, pu.data_adaugare FROM produse p
                 JOIN produse_urmarite pu ON p.id = pu.produs_id
                 WHERE pu.user_id=?
                 ORDER BY pu.data_adaugare DESC''', (user_id,))
    produse = c.fetchall()
    conn.close()
    return produse

def este_urmarit(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM produse_urmarite WHERE user_id=? AND produs_id=?',
              (user_id, produs_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def salveaza_vizita(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO istoric_vizite (user_id, produs_id) VALUES (?,?)',
              (user_id, produs_id))
    conn.commit()
    conn.close()

def get_istoric_vizite(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT DISTINCT p.*, iv.data_vizita FROM produse p
                 JOIN istoric_vizite iv ON p.id = iv.produs_id
                 WHERE iv.user_id=?
                 ORDER BY iv.data_vizita DESC LIMIT 20''', (user_id,))
    produse = c.fetchall()
    conn.close()
    return produse

def get_alerte_user(email):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT a.*, p.nume, p.link, p.poza, p.pret_curent
                 FROM alerte a
                 JOIN produse p ON a.produs_id = p.id
                 WHERE a.email=? AND a.activa=1
                 ORDER BY a.data_creare DESC''', (email,))
    alerte = c.fetchall()
    conn.close()
    return alerte

def sterge_alerta(alerta_id, email):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE alerte SET activa=0 WHERE id=? AND email=?', (alerta_id, email))
    conn.commit()
    conn.close()

def schimba_parola(user_id, password_hash):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET password_hash=? WHERE id=?', (password_hash, user_id))
    conn.commit()
    conn.close()

def schimba_username(user_id, username):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET username=? WHERE id=?', (username, user_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
