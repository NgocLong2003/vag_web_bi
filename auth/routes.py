import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from database import get_db, hash_password, log_activity, sql_now
from auth import login_required

bp = Blueprint('auth', __name__)


@bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard_list'))
    return redirect(url_for('auth.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        pw_hash = hash_password(request.form.get('password', ''))
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password_hash = ? AND is_active = 1',
                          (username, pw_hash)).fetchone()
        if user:
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['token'] = secrets.token_hex(16)
            db.execute(f'UPDATE users SET last_login = {sql_now()} WHERE id = ?', (user['id'],))
            db.commit()
            log_activity(user['id'], 'login')
            return redirect(url_for('dashboard.dashboard_list'))
        else:
            error = 'Sai tên đăng nhập hoặc mật khẩu'
    return render_template('login.html', error=error)


@bp.route('/logout')
def logout():
    if 'user_id' in session:
        log_activity(session['user_id'], 'logout')
    session.clear()
    return redirect(url_for('auth.login'))


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    db = get_db()
    user = g.current_user
    if request.method == 'POST':
        display_name = request.form.get('display_name', '').strip()
        new_password = request.form.get('new_password', '').strip()
        current_password = request.form.get('current_password', '')
        if hash_password(current_password) != user['password_hash']:
            flash('Mật khẩu hiện tại không đúng', 'error')
            return redirect(url_for('auth.user_settings'))
        if new_password:
            db.execute('UPDATE users SET display_name=?, password_hash=?, password_plain=? WHERE id=?',
                       (display_name, hash_password(new_password), new_password, user['id']))
        else:
            db.execute('UPDATE users SET display_name=? WHERE id=?', (display_name, user['id']))
        db.commit()
        flash('Đã cập nhật thông tin', 'success')
        return redirect(url_for('auth.user_settings'))
    return render_template('settings.html', user=user,
        username=user['display_name'] or user['username'], role=user['role'])