import psycopg2
import psycopg2.extras
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = "postgresql://postgres:jwsMqrNEFqNmBpeiddHvZGixGwCujlrB@shinkansen.proxy.rlwy.net:12071/railway"

def row_to_dict(row):
    if row is None:
        return None
    return dict(row)

def rows_to_list(rows):
    return [dict(r) for r in rows]

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
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
    c.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    conn.commit()
    conn.close()
    print("✅ Baza de date initializata!")

def get_produs(produs_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT * FROM produse WHERE id = %s", (produs_id,))
    produs = c.fetchone()
    conn.close()
    return row_to_dict(produs)

def get_istoric(produs_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT * FROM istoric_preturi WHERE produs_id = %s ORDER BY data DESC LIMIT 30", (produs_id,))
    istoric = c.fetchall()
    conn.close()
    return rows_to_list(istoric)

def salveaza_alerta(produs_id, email, pret_dorit):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO alerte (produs_id, email, pret_dorit) VALUES (%s, %s, %s)", (produs_id, email, pret_dorit))
    conn.commit()
    conn.close()

def get_alerte_user(email):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("""
        SELECT a.*, p.nume, p.pret_curent, p.poza
        FROM alerte a
        JOIN produse p ON a.produs_id = p.id
        WHERE a.email = %s AND a.activa = 1
    """, (email,))
    alerte = c.fetchall()
    conn.close()
    return rows_to_list(alerte)

def sterge_alerta(alerta_id, email=None):
    conn = get_db()
    c = conn.cursor()
    if email:
        c.execute("DELETE FROM alerte WHERE id = %s AND email = %s", (alerta_id, email))
    else:
        c.execute("DELETE FROM alerte WHERE id = %s", (alerta_id,))
    conn.commit()
    conn.close()

def schimba_parola(user_id, parola_noua):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET password = %s WHERE id = %s", (parola_noua, user_id))
    conn.commit()
    conn.close()

def schimba_username(user_id, username_nou):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET username = %s WHERE id = %s", (username_nou, user_id))
    conn.commit()
    conn.close()

def urmareste_produs(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO urmariri (user_id, produs_id) VALUES (%s, %s)", (user_id, produs_id))
        conn.commit()
    except:
        conn.rollback()
    conn.close()

def sterge_urmarire(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM urmariri WHERE user_id = %s AND produs_id = %s", (user_id, produs_id))
    conn.commit()
    conn.close()

def get_produse_urmarite(user_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("""
        SELECT p.* FROM produse p
        JOIN urmariri u ON p.id = u.produs_id
        WHERE u.user_id = %s
    """, (user_id,))
    produse = c.fetchall()
    conn.close()
    return rows_to_list(produse)

def este_urmarit(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM urmariri WHERE user_id = %s AND produs_id = %s", (user_id, produs_id))
    rezultat = c.fetchone()
    conn.close()
    return rezultat is not None

def salveaza_vizita(user_id, produs_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO vizite (user_id, produs_id) VALUES (%s, %s)", (user_id, produs_id))
    conn.commit()
    conn.close()

def get_istoric_vizite(user_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("""
        SELECT p.*, v.data as data_vizita FROM produse p
        JOIN vizite v ON p.id = v.produs_id
        WHERE v.user_id = %s
        ORDER BY v.data DESC LIMIT 20
    """, (user_id,))
    vizite = c.fetchall()
    conn.close()
    return rows_to_list(vizite)

def cauta_produse_db(query):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cuvinte = query.lower().split()
    conditii = " AND ".join([f"LOWER(nume) LIKE %s" for _ in cuvinte])
    valori = [f'%{cuvant}%' for cuvant in cuvinte]
    c.execute(f"SELECT * FROM produse WHERE {conditii}", valori)
    produse = c.fetchall()
    if not produse:
        # Fuzzy per cuvânt: fiecare cuvânt trebuie să apară similar în nume (prinde typo-uri, nu produse diferite)
        conditii_fuzzy = " AND ".join([f"word_similarity(%s, LOWER(nume)) > 0.3" for _ in cuvinte])
        order_expr = " + ".join([f"word_similarity(%s, LOWER(nume))" for _ in cuvinte])
        c.execute(
            f"SELECT * FROM produse WHERE {conditii_fuzzy} ORDER BY {order_expr} DESC",
            cuvinte + cuvinte
        )
        produse = c.fetchall()
    conn.close()
    return rows_to_list(produse)

def salveaza_produs(emag_id, nume, link, poza, pret):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        c.execute("""
            INSERT INTO produse (emag_id, nume, link, poza, pret_curent)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (emag_id) DO UPDATE
            SET pret_curent = %s, nume = %s
            RETURNING id
        """, (emag_id, nume, link, poza, pret, pret, nume))
        produs_id = c.fetchone()['id']
        c.execute("INSERT INTO istoric_preturi (produs_id, pret) VALUES (%s, %s)", (produs_id, pret))
        conn.commit()
        conn.close()
        return produs_id
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e
