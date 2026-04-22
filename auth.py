from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from database import get_db
from authlib.integrations.flask_client import OAuth
import psycopg2.extras

auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()
login_manager = LoginManager()
oauth = OAuth()

class User(UserMixin):
    def __init__(self, id, email, username, avatar=None):
        self.id = id
        self.email = email
        self.username = username
        self.avatar = avatar

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute('SELECT * FROM users WHERE id=%s', (user_id,))
    u = c.fetchone()
    conn.close()
    if u:
        return User(u['id'], u['email'], u['username'], u.get('avatar'))
    return None

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute('SELECT id FROM users WHERE email=%s', (email,))
        if c.fetchone():
            flash('Email deja inregistrat!', 'error')
            conn.close()
            return redirect(url_for('auth.register'))
        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        c.execute('INSERT INTO users (email, username, password) VALUES (%s,%s,%s) RETURNING id',
                  (email, username, pw_hash))
        user_id = c.fetchone()['id']
        conn.commit()
        conn.close()
        login_user(User(user_id, email, username), remember=True)
        flash('Cont creat cu succes!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = get_db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute('SELECT * FROM users WHERE email=%s', (email,))
        u = c.fetchone()
        conn.close()
        if u and u['password'] and bcrypt.check_password_hash(u['password'], password):
            login_user(User(u['id'], u['email'], u['username'], u.get('avatar')), remember=True)
            return redirect(url_for('index'))
        flash('Email sau parola gresita!', 'error')
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@auth.route('/login/google')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth.route('/login/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    userinfo = token['userinfo']
    return _oauth_login(
        oauth_id=userinfo['sub'],
        email=userinfo['email'],
        username=userinfo.get('name', ''),
        avatar=userinfo.get('picture', ''),
        provider='google'
    )

@auth.route('/login/facebook')
def facebook_login():
    redirect_uri = url_for('auth.facebook_callback', _external=True)
    return oauth.facebook.authorize_redirect(redirect_uri)

@auth.route('/login/facebook/callback')
def facebook_callback():
    token = oauth.facebook.authorize_access_token()
    resp = oauth.facebook.get('https://graph.facebook.com/me?fields=id,name,email,picture')
    profile = resp.json()
    return _oauth_login(
        oauth_id=profile['id'],
        email=profile.get('email', ''),
        username=profile.get('name', ''),
        avatar=profile.get('picture', {}).get('data', {}).get('url', ''),
        provider='facebook'
    )

def _oauth_login(oauth_id, email, username, avatar, provider):
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    col = f'{provider}_id'
    c.execute(f'SELECT * FROM users WHERE {col}=%s', (oauth_id,))
    u = c.fetchone()
    if not u and email:
        c.execute('SELECT * FROM users WHERE email=%s', (email,))
        u = c.fetchone()
    if not u:
        c.execute(f'INSERT INTO users (email, username, avatar, {col}) VALUES (%s,%s,%s,%s) RETURNING id',
                  (email, username, avatar, oauth_id))
        user_id = c.fetchone()['id']
        conn.commit()
    else:
        user_id = u['id']
        c.execute(f'UPDATE users SET {col}=%s, avatar=%s WHERE id=%s', (oauth_id, avatar, user_id))
        conn.commit()
    conn.close()
    login_user(User(user_id, email, username, avatar), remember=True)
    return redirect(url_for('index'))
