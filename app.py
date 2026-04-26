from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import current_user, login_required
from flask_cors import CORS
from whitenoise import WhiteNoise
from database import init_db, get_produs, get_istoric, salveaza_alerta, get_alerte_user, sterge_alerta, schimba_parola, schimba_username, urmareste_produs, sterge_urmarire, get_produse_urmarite, este_urmarit, salveaza_vizita, get_istoric_vizite, cauta_produse_db, salveaza_produs, get_user_by_email, sterge_cont_complet
from scraper import cauta_emag, cauta_emag_pagina, scrape_produs, salveaza_rezultate
from scheduler import start_scheduler
from auth import auth, bcrypt, login_manager, oauth
import asyncio
import threading
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, resources={r"/api/extensie.*": {"origins": "*"}})
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'pricetracker2025secret2026')
app.config['REMEMBER_COOKIE_DURATION'] = 2592000
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')
app.config['FACEBOOK_CLIENT_ID'] = os.getenv('FACEBOOK_CLIENT_ID')
app.config['FACEBOOK_CLIENT_SECRET'] = os.getenv('FACEBOOK_CLIENT_SECRET')

bcrypt.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
oauth.init_app(app)

oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

oauth.register(
    name='facebook',
    client_id=app.config['FACEBOOK_CLIENT_ID'],
    client_secret=app.config['FACEBOOK_CLIENT_SECRET'],
    access_token_url='https://graph.facebook.com/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    client_kwargs={'scope': 'email'}
)

app.register_blueprint(auth)
init_db()

scraping_jobs = {}

def _run_background_scrape(query, pagini):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for pagina in pagini:
            try:
                rezultate = loop.run_until_complete(cauta_emag_pagina(query, pagina))
                if rezultate:
                    salveaza_rezultate(rezultate)
                    print(f"Bg scrape p{pagina}: {len(rezultate)} produse")
            except Exception as e:
                print(f"Bg scrape p{pagina} eroare: {e}")
        loop.close()
    finally:
        scraping_jobs[query.lower()]['done'] = True
        print(f"Bg scrape terminat: '{query}'")
start_scheduler()

@app.route('/')
def index():
    query = request.args.get('q', '')
    produse = []
    if query:
        produse = cauta_produse_db(query)
    return render_template('index.html', produse=produse, query=query)

@app.route('/produs/<int:produs_id>')
def produs(produs_id):
    p = get_produs(produs_id)
    if not p:
        return redirect(url_for('index'))
    if current_user.is_authenticated:
        salveaza_vizita(current_user.id, produs_id)
    istoric = get_istoric(produs_id)
    istoric_json = [{"data": str(row['data'])[:10], "pret": row['pret']} for row in istoric]
    pret_min = min((r['pret'] for r in istoric_json), default=0)
    pret_max = max((r['pret'] for r in istoric_json), default=0)
    urmarit = este_urmarit(current_user.id, produs_id) if current_user.is_authenticated else False
    return render_template('produs.html', produs=p, istoric=istoric_json,
                           pret_min=pret_min, pret_max=pret_max, urmarit=urmarit)

@app.route('/urmareste/<int:produs_id>')
@login_required
def urmareste(produs_id):
    urmareste_produs(current_user.id, produs_id)
    flash('Produs urmarit!', 'success')
    return redirect(url_for('produs', produs_id=produs_id))

@app.route('/sterge-urmarire/<int:produs_id>')
@login_required
def sterge_urmarire_route(produs_id):
    sterge_urmarire(current_user.id, produs_id)
    flash('Urmarire stearsa!', 'success')
    return redirect(url_for('produs', produs_id=produs_id))

@app.route('/profil')
@login_required
def profil():
    alerte = get_alerte_user(current_user.email)
    urmarite = get_produse_urmarite(current_user.id)
    vizite = get_istoric_vizite(current_user.id)
    return render_template('profil.html', alerte=alerte, urmarite=urmarite, vizite=vizite)

@app.route('/sterge-alerta/<int:alerta_id>')
@login_required
def sterge_alerta_route(alerta_id):
    sterge_alerta(alerta_id, current_user.email)
    flash('Alerta stearsa!', 'success')
    return redirect(url_for('profil'))

@app.route('/profil/username', methods=['POST'])
@login_required
def schimba_username_route():
    username = request.form.get('username')
    schimba_username(current_user.id, username)
    flash('Username actualizat!', 'success')
    return redirect(url_for('profil'))

@app.route('/profil/parola', methods=['POST'])
@login_required
def schimba_parola_route():
    parola_noua = request.form.get('parola_noua')
    confirmare = request.form.get('confirmare')
    if parola_noua != confirmare:
        flash('Parolele nu coincid!', 'error')
        return redirect(url_for('profil'))
    pw_hash = bcrypt.generate_password_hash(parola_noua).decode('utf-8')
    schimba_parola(current_user.id, pw_hash)
    flash('Parola schimbata cu succes!', 'success')
    return redirect(url_for('profil'))

@app.route('/alerta', methods=['POST'])
def alerta():
    produs_id = request.form.get('produs_id')
    email = request.form.get('email')
    pret_dorit = request.form.get('pret_dorit')
    if not all([produs_id, email, pret_dorit]):
        return jsonify({"status": "error", "mesaj": "Date incomplete"}), 400
    try:
        salveaza_alerta(int(produs_id), email, float(pret_dorit))
        return jsonify({"status": "ok", "mesaj": "Alerta setata cu succes!"})
    except Exception as e:
        return jsonify({"status": "error", "mesaj": str(e)}), 500

@app.route('/23e71b655a3c0a565d2868686180808d')
def profitshare_validation():
    return '', 200

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"produse": [], "status": "done"})

    query_key = query.lower()
    produse = cauta_produse_db(query)
    job = scraping_jobs.get(query_key)

    if job is None:
        if not produse:
            # Scrape pagina 1 sincron ca să avem rezultate imediat
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                rezultate = loop.run_until_complete(cauta_emag(query))
                loop.close()
                print(f"Sync scrape p1: {len(rezultate)} produse")
                salveaza_rezultate(rezultate)
                produse = cauta_produse_db(query)
            except Exception as e:
                print(f"Eroare sync scrape: {e}")

        # Paginile 2-3 în background
        scraping_jobs[query_key] = {'done': False}
        t = threading.Thread(target=_run_background_scrape, args=(query, [2, 3]), daemon=True)
        t.start()

    status = "done" if scraping_jobs.get(query_key, {}).get('done', True) else "scraping"
    return jsonify({"produse": produse, "status": status})


SURSE_VALIDE = {
    'emag.ro', 'altex.ro', 'flanco.ro', 'cel.ro', 'pcgarage.ro',
    'evomag.ro', 'mediagalaxy.ro', 'dedeman.ro', 'ikea.com', 'zara.com',
}

def _link_valid(link):
    try:
        from urllib.parse import urlparse
        host = (urlparse(link).hostname or '').replace('www.', '')
        return any(host == d or host.endswith('.' + d) for d in SURSE_VALIDE)
    except Exception:
        return False


@app.route('/api/extensie', methods=['POST', 'OPTIONS'])
def api_extensie():
    if request.method == 'OPTIONS':
        return '', 204

    print(f"[extensie] POST primit de la {request.headers.get('Origin', 'N/A')}")

    data = request.get_json(silent=True)
    if not data:
        print("[extensie] EROARE: body gol sau non-JSON")
        return jsonify({"status": "error", "mesaj": "JSON asteptat"}), 400

    emag_id  = str(data.get('emag_id', '')).strip()
    nume     = str(data.get('nume',    '')).strip()
    link     = str(data.get('link',    '')).strip()
    poza     = str(data.get('poza',    '')).strip()
    sursa    = str(data.get('sursa',   'eMAG')).strip()
    pret_raw = data.get('pret')

    print(f"[extensie] sursa={sursa} | id={emag_id} | pret={pret_raw} | nume={nume[:60]!r}")

    if not emag_id or not nume or not link or pret_raw is None:
        print(f"[extensie] EROARE: câmpuri lipsă – emag_id={bool(emag_id)} nume={bool(nume)} link={bool(link)} pret={pret_raw is not None}")
        return jsonify({"status": "error", "mesaj": "Lipsesc: emag_id, nume, link, pret"}), 400

    if not _link_valid(link):
        print(f"[extensie] EROARE: link invalid – {link[:80]}")
        return jsonify({"status": "error", "mesaj": "Link invalid – magazin nesupportat"}), 400

    try:
        pret = float(pret_raw)
        if pret <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        print(f"[extensie] EROARE: pret invalid – {pret_raw!r}")
        return jsonify({"status": "error", "mesaj": "Pret invalid"}), 400

    try:
        produs_id = salveaza_produs(emag_id, nume, link, poza, pret, sursa)
        print(f"[extensie] OK – produs_id={produs_id} | {sursa} | {pret} Lei | {emag_id}")
        return jsonify({
            "status":    "ok",
            "mesaj":     "Produs salvat!",
            "produs_id": produs_id,
            "url":       f"https://www.pretalert.ro/produs/{produs_id}"
        })
    except Exception as e:
        print(f"[extensie] EROARE DB: {e}")
        return jsonify({"status": "error", "mesaj": str(e)}), 500


@app.route('/api/extensie/favorit', methods=['POST', 'OPTIONS'])
def api_extensie_favorit():
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json(silent=True) or {}
    produs_id = data.get('produs_id')
    email     = str(data.get('email', '')).strip().lower()

    if not produs_id or not email:
        return jsonify({"status": "error", "mesaj": "Lipsesc produs_id sau email"}), 400

    user = get_user_by_email(email)
    if not user:
        return jsonify({"status": "error", "mesaj": "Nu există cont PretAlert cu acest email"}), 404

    try:
        urmareste_produs(user['id'], int(produs_id))
        print(f"[extensie/favorit] user={user['id']} produs={produs_id}")
        return jsonify({"status": "ok", "mesaj": "Adăugat la favorite!"})
    except Exception as e:
        return jsonify({"status": "error", "mesaj": str(e)}), 500


@app.route('/api/extensie/alerta', methods=['POST', 'OPTIONS'])
def api_extensie_alerta():
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json(silent=True) or {}
    produs_id  = data.get('produs_id')
    email      = str(data.get('email', '')).strip().lower()
    pret_dorit = data.get('pret_dorit')

    if not produs_id or not email or pret_dorit is None:
        return jsonify({"status": "error", "mesaj": "Lipsesc produs_id, email sau pret_dorit"}), 400

    try:
        pret = float(pret_dorit)
        if pret <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"status": "error", "mesaj": "Preț dorit invalid"}), 400

    try:
        salveaza_alerta(int(produs_id), email, pret)
        print(f"[extensie/alerta] produs={produs_id} pret_dorit={pret}")
        return jsonify({"status": "ok", "mesaj": "Alertă setată!"})
    except Exception as e:
        return jsonify({"status": "error", "mesaj": str(e)}), 500


@app.route('/sterge-cont', methods=['POST'])
@login_required
def sterge_cont():
    from flask_login import logout_user
    sterge_cont_complet(current_user.id, current_user.email)
    logout_user()
    flash('Contul și toate datele tale au fost șterse complet.', 'success')
    return redirect(url_for('index'))

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
