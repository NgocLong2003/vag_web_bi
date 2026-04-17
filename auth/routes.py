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
            return redirect('/')    
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

@bp.route('/api/me')
@login_required
def api_me():
    """API: trả thông tin user đang login (JSON)"""
    from flask import jsonify
    user = g.current_user
    db = get_db()
 
    # Lấy danh sách dashboard được phân quyền
    if user['role'] == 'admin':
        dashboards = db.execute(
            'SELECT id, slug, name, dashboard_type FROM dashboards WHERE is_active = 1 ORDER BY sort_order'
        ).fetchall()
    else:
        dashboards = db.execute('''
            SELECT d.id, d.slug, d.name, d.dashboard_type
            FROM dashboards d JOIN user_dashboards ud ON d.id = ud.dashboard_id
            WHERE ud.user_id = ? AND d.is_active = 1 ORDER BY d.sort_order
        ''', (user['id'],)).fetchall()
 
    # Lấy danh sách BP được phân quyền
    ma_bp_raw = user['ma_bp'] or ''
    allowed_bps = [b.strip() for b in ma_bp_raw.split(',') if b.strip()]
 
    # Lấy danh sách mã NVKD
    nvkd_raw = user['ma_nvkd_list'] or ''
    ma_nvkd_list = [n.strip() for n in nvkd_raw.split(',') if n.strip()]
 
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'display_name': user['display_name'] or user['username'],
            'role': user['role'],
            'khoi': user['khoi'] or '',
            'bo_phan': user['bo_phan'] or '',
            'chuc_vu': user['chuc_vu'] or '',
            'ma_bp': ma_bp_raw,
            'ma_nvkd_list': nvkd_raw,
            'email': user['email'] or '',
            'is_active': user['is_active'],
        },
        'permissions': {
            'allowed_bps': allowed_bps,
            'ma_nvkd_list': ma_nvkd_list,
            'dashboards': [
                {'id': d['id'], 'slug': d['slug'], 'name': d['name'], 'type': d['dashboard_type']}
                for d in dashboards
            ],
        }
    })

@bp.route('/api/dashboards')
@login_required
def api_dashboards():
    """API: trả danh sách dashboard user được phép xem (JSON)"""
    from flask import jsonify
    db = get_db()
    user = g.current_user
 
    if user['role'] == 'admin':
        rows = db.execute(
            'SELECT * FROM dashboards WHERE is_active = 1 ORDER BY sort_order, name'
        ).fetchall()
    else:
        rows = db.execute('''
            SELECT d.* FROM dashboards d
            JOIN user_dashboards ud ON d.id = ud.dashboard_id
            WHERE ud.user_id = ? AND d.is_active = 1
            ORDER BY d.sort_order, d.name
        ''', (user['id'],)).fetchall()
 
    dashboards = []
    for d in rows:
        dashboards.append({
            'id': d['id'],
            'slug': d['slug'],
            'name': d['name'],
            'description': d['description'] or '',
            'dashboard_type': d['dashboard_type'] or 'powerbi',
            'powerbi_url': d['powerbi_url'] or '',
            'sort_order': d['sort_order'] or 0,
            # Các cột mới (nếu chưa có thì trả default)
            'icon_svg': d['icon_svg'] if 'icon_svg' in d.keys() else '',
            'color': d['color'] if 'color' in d.keys() else 'teal',
        })
 
    return jsonify({'success': True, 'data': dashboards})