"""admin/users.py — User CRUD + bulk create"""
from flask import request, redirect, url_for, session, abort, flash, g
from database import get_db, hash_password
from auth import admin_required
from admin import bp, _admin_bp_list, _filter_users_by_bp, _can_manage_user, _log_audit, _diff_user


@bp.route('/user/add', methods=['POST'])
@admin_required
def user_add():
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    display_name = request.form.get('display_name', '').strip()
    khoi = request.form.get('khoi', '').strip()
    bo_phan = request.form.get('bo_phan', '').strip()
    chuc_vu = request.form.get('chuc_vu', '').strip()
    ma_nvkd_list = request.form.get('ma_nvkd_list', '').strip()
    email = request.form.get('email', '').strip()
    ma_bp = request.form.get('ma_bp', '').strip()
    role = request.form.get('role', 'user')
    if not username or not password:
        flash('Tên đăng nhập và mật khẩu không được để trống', 'error')
        return redirect(url_for('admin.admin_index') + '#users')
    if not ma_nvkd_list:
        flash('Mã NVKD không được để trống', 'error')
        return redirect(url_for('admin.admin_index') + '#users')

    admin_bps = _admin_bp_list()
    if admin_bps and ma_bp:
        new_bps = set(b.strip() for b in ma_bp.split(',') if b.strip())
        if not new_bps.issubset(set(admin_bps)):
            flash('Bạn không có quyền gán BP ngoài phạm vi quản lý', 'error')
            return redirect(url_for('admin.admin_index') + '#users')

    if role not in ('admin', 'user'):
        role = 'user'
    db = get_db()
    try:
        db.execute('INSERT INTO users (username, password_hash, password_plain, display_name, khoi, bo_phan, chuc_vu, ma_nvkd_list, email, ma_bp, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   (username, hash_password(password), password, display_name, khoi, bo_phan, chuc_vu, ma_nvkd_list, email, ma_bp, role))
        db.commit()
        row = db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        if row:
            new_uid = row['id'] if isinstance(row, dict) else row[0]
            dash_ids = request.form.getlist('dash_ids')
            for did in dash_ids:
                try:
                    db.execute('INSERT INTO user_dashboards (user_id, dashboard_id) VALUES (?, ?)', (new_uid, int(did)))
                except Exception:
                    pass
            db.commit()
        flash(f'Đã tạo tài khoản "{username}"', 'success')
        if row:
            _log_audit('create', new_uid, username, {
                'display_name': display_name, 'ma_nvkd_list': ma_nvkd_list,
                'ma_bp': ma_bp, 'role': role, 'khoi': khoi, 'bo_phan': bo_phan,
                'dash_ids': request.form.getlist('dash_ids')
            })
    except Exception as e:
        err = str(e).lower()
        if 'unique' in err or 'duplicate' in err:
            flash(f'Tên đăng nhập "{username}" đã tồn tại', 'error')
        else:
            flash(f'Lỗi: {e}', 'error')
    return redirect(url_for('admin.admin_index') + '#users')


@bp.route('/user/<int:user_id>/edit', methods=['POST'])
@admin_required
def user_edit(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        abort(404)
    admin_bps = _admin_bp_list()
    if not _can_manage_user(admin_bps, user):
        flash('Bạn không có quyền chỉnh sửa user này', 'error')
        return redirect(url_for('admin.admin_index') + '#users')

    display_name = request.form.get('display_name', '').strip()
    khoi = request.form.get('khoi', '').strip()
    bo_phan = request.form.get('bo_phan', '').strip()
    chuc_vu = request.form.get('chuc_vu', '').strip()
    ma_nvkd_list = request.form.get('ma_nvkd_list', '').strip()
    email = request.form.get('email', '').strip()
    ma_bp = request.form.get('ma_bp', '').strip()
    role = request.form.get('role', 'user')
    is_active = 1 if request.form.get('is_active') else 0
    new_password = request.form.get('new_password', '').strip()

    if not ma_nvkd_list:
        flash('Mã NVKD không được để trống', 'error')
        return redirect(url_for('admin.admin_index') + '#users')
    if admin_bps and ma_bp:
        new_bps = set(b.strip() for b in ma_bp.split(',') if b.strip())
        if not new_bps.issubset(set(admin_bps)):
            flash('Bạn không có quyền gán BP ngoài phạm vi quản lý', 'error')
            return redirect(url_for('admin.admin_index') + '#users')
    if role not in ('admin', 'user'):
        role = 'user'

    new_data = {'display_name': display_name, 'khoi': khoi, 'bo_phan': bo_phan,
                'chuc_vu': chuc_vu, 'ma_nvkd_list': ma_nvkd_list, 'email': email,
                'ma_bp': ma_bp, 'role': role, 'is_active': str(is_active)}
    changes = _diff_user(user, new_data)
    if new_password:
        changes['password'] = {'old': '***', 'new': '(đã đổi)'}

    if new_password:
        db.execute('UPDATE users SET display_name=?, khoi=?, bo_phan=?, chuc_vu=?, ma_nvkd_list=?, email=?, ma_bp=?, role=?, is_active=?, password_hash=?, password_plain=? WHERE id=?',
                    (display_name, khoi, bo_phan, chuc_vu, ma_nvkd_list, email, ma_bp, role, is_active, hash_password(new_password), new_password, user_id))
    else:
        db.execute('UPDATE users SET display_name=?, khoi=?, bo_phan=?, chuc_vu=?, ma_nvkd_list=?, email=?, ma_bp=?, role=?, is_active=? WHERE id=?',
                    (display_name, khoi, bo_phan, chuc_vu, ma_nvkd_list, email, ma_bp, role, is_active, user_id))
    db.commit()
    dash_ids = request.form.getlist('dash_ids')
    db.execute('DELETE FROM user_dashboards WHERE user_id=?', (user_id,))
    for did in dash_ids:
        try:
            db.execute('INSERT INTO user_dashboards (user_id, dashboard_id) VALUES (?, ?)', (user_id, int(did)))
        except Exception:
            pass
    db.commit()
    if changes:
        _log_audit('edit', user_id, user['username'], changes)
    flash('Đã cập nhật user', 'success')
    return redirect(url_for('admin.admin_index') + '#users')


@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def user_delete(user_id):
    if user_id == session.get('user_id'):
        flash('Không thể xóa tài khoản đang đăng nhập', 'error')
        return redirect(url_for('admin.admin_index') + '#users')
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        abort(404)
    admin_bps = _admin_bp_list()
    if not _can_manage_user(admin_bps, user):
        flash('Bạn không có quyền xóa user này', 'error')
        return redirect(url_for('admin.admin_index') + '#users')
    _log_audit('delete', user_id, user['username'], {
        'display_name': user['display_name'] or '', 'ma_nvkd_list': user['ma_nvkd_list'] or '',
        'ma_bp': user['ma_bp'] or '', 'role': user['role'] or ''
    })
    db.execute('DELETE FROM user_dashboards WHERE user_id = ?', (user_id,))
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    flash('Đã xóa user', 'success')
    return redirect(url_for('admin.admin_index') + '#users')


@bp.route('/bulk-create-users', methods=['POST'])
@admin_required
def bulk_create_users():
    import json
    try:
        from config import SQLSERVER_CONFIG
        import pyodbc
        c = SQLSERVER_CONFIG
        conn = pyodbc.connect(
            f"DRIVER={{{c['driver']}}};SERVER={c['server']},{c['port']};"
            f"DATABASE={c['database']};UID={c['username']};PWD={c['password']};"
            "TrustServerCertificate=yes;Connect Timeout=30;")
        cur = conn.cursor()
        cur.execute("""
            SELECT ten_nvkd, ma_nvkd, ma_bp
            FROM [dbo].[DMKHACHHANG_VIEW]
            GROUP BY ma_nvkd, ten_nvkd, ma_bp
            HAVING ma_nvkd != ''
        """)
        nv_list = [{'ten_nvkd': row[0] or '', 'ma_nvkd': row[1] or '', 'ma_bp': row[2] or ''} for row in cur.fetchall()]
        conn.close()
    except Exception as e:
        return json.dumps({'ok': False, 'error': f'SQL Server error: {e}'}), 500

    db = get_db()
    created = skipped = 0
    for nv in nv_list:
        ma = nv['ma_nvkd'].strip()
        ten = nv['ten_nvkd'].strip()
        mbp = nv['ma_bp'].strip()
        if not ma:
            continue
        username = ma.lower()
        password = (mbp + '123' + ma).lower()
        if db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
            skipped += 1
            continue
        try:
            db.execute(
                'INSERT INTO users (username, password_hash, password_plain, display_name, ma_nvkd_list, ma_bp, role) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (username, hash_password(password), password, ten, ma, mbp, 'user'))
            created += 1
        except Exception:
            skipped += 1
    db.commit()
    return json.dumps({'ok': True, 'created': created, 'skipped': skipped, 'total': len(nv_list)})