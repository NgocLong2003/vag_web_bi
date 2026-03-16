from functools import wraps
from flask import session, redirect, url_for, abort, g
from database import get_db


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or 'token' not in session:
            session.clear()
            return redirect(url_for('auth.login'))
        user = get_db().execute('SELECT * FROM users WHERE id = ? AND is_active = 1',
                                (session['user_id'],)).fetchone()
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        user = get_db().execute('SELECT * FROM users WHERE id = ? AND is_active = 1',
                                (session['user_id'],)).fetchone()
        if not user or user['role'] != 'admin':
            abort(403)
        g.current_user = user
        return f(*args, **kwargs)
    return decorated