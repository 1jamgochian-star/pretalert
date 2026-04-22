from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import current_user
from database import init_db, get_produs, get_istoric, salveaza_alerta
from scraper import cauta_emag, scrape_produs, salveaza_rezultate
from scheduler import start_scheduler
from auth import auth, bcrypt, login_manager, oauth
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'pricetracker2025secret'

# Google OAuth
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

# Facebook OAuth
app.config['FACEBOOK_CLIENT_ID'] = os.getenv('FACEBOOK_CLIENT_ID')
app.config['FACEBOOK_CLIENT_SECRET'] = os.getenv('FACEBOOK_CLIENT_SECRET')

# Init extensions
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

# Initializeaza DB
init_db()
start_scheduler()
@app.route('/')
def index():
    query = request.args.get('q', '')
    produse = []
    if query:
        produse = salveaza_rezultate(asyncio.run(cauta_emag(query)))
    return render_template('index.html', produse=produse, query=query)

from flask_login import login_required, current_user
from database import get_alerte_user, sterge_alerta, schimba_parola, schimba_username

@app.route('/profil')
@login_required
def profil():
    alerte = get_alerte_user(current_user.email)
    return render_template('profil.html', alerte=alerte)

@app.route('/sterge-alerta/<int:alerta_id>')
@login_required
def sterge_alerta_route(alerta_id):
    sterge_alerta(alerta_id, current_user.email)
    flash('Alertă ștearsă!', 'success')
    return redirect(url_for('profil'))

@app.route('/profil/username', methods=['POST'])
@login_required
def schimba_username_route():
    username = request.form.get('username')
    schimba_username(current_user.id, username)
    current_user.username = username
    flash('Username actualizat!', 'success')
    return redirect(url_for('profil'))

@app.route('/profil/parola', methods=['POST'])
@login_required
def schimba_parola_route():
    from flask_bcrypt import Bcrypt
    bcrypt_inst = Bcrypt()
    parola_noua = request.form.get('parola_noua')
    confirmare = request.form.get('confirmare')
    if parola_noua != confirmare:
        flash('Parolele nu coincid!', 'error')
        return redirect(url_for('profil'))
    pw_hash = bcrypt.generate_password_hash(parola_noua).decode('utf-8')
    schimba_parola(current_user.id, pw_hash)
    flash('Parola schimbată cu succes!', 'success')
    return redirect(url_for('profil'))

@app.route('/produs/<int:produs_id>')
def produs(produs_id):
    p = get_produs(produs_id)
    if not p:
        return redirect(url_for('index'))
    istoric = get_istoric(produs_id)
    istoric_json = [{"data": row['data'][:10], "pret": row['pret']} for row in istoric]
    pret_min = min((r['pret'] for r in istoric_json), default=0)
    pret_max = max((r['pret'] for r in istoric_json), default=0)
    return render_template('produs.html', produs=p, istoric=istoric_json,
                           pret_min=pret_min, pret_max=pret_max)

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

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    produse = asyncio.run(cauta_emag(query))
    return jsonify(produse[:10])

    app.run(debug=True, port=5000)
