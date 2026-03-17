from flask import Blueprint, render_template, request, redirect, url_for, session, abort, flash, g
from database import get_db, hash_password, sql_now
from auth import admin_required

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
@admin_required
def admin_index():
    db = get_db()
    users = db.execute('SELECT * FROM users ORDER BY role DESC, username').fetchall()
    dashboards = db.execute('SELECT * FROM dashboards ORDER BY sort_order, name').fetchall()
    dash_user_counts = {}
    for d in dashboards:
        dash_user_counts[d['id']] = db.execute(
            'SELECT COUNT(*) FROM user_dashboards WHERE dashboard_id = ?', (d['id'],)).fetchone()[0]
    user_dash_map = {}
    for u in users:
        rows = db.execute('SELECT dashboard_id FROM user_dashboards WHERE user_id = ?', (u['id'],)).fetchall()
        user_dash_map[u['id']] = [r['dashboard_id'] for r in rows]

    # Lấy danh sách mã BP từ DMKHACHHANG_VIEW (nếu SQL Server)
    all_bp = []
    try:
        bp_rows = db.execute("SELECT DISTINCT ma_bp FROM DMKHACHHANG_VIEW WHERE ma_bp IS NOT NULL AND ma_bp != '' AND ma_bp != 'TN' ORDER BY ma_bp").fetchall()
        all_bp = [r['ma_bp'] for r in bp_rows]
    except:
        pass

    # Lấy danh sách kỳ báo cáo
    ky_bao_cao = []
    try:
        ky_bao_cao = db.execute('SELECT * FROM ky_bao_cao ORDER BY ngay_bd_xuat_ban DESC').fetchall()
    except:
        pass

    return render_template('admin.html', users=users, dashboards=dashboards,
        dash_user_counts=dash_user_counts, user_dash_map=user_dash_map, all_bp=all_bp,
        ky_bao_cao=ky_bao_cao,
        username=g.current_user['display_name'] or g.current_user['username'])


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
    if role not in ('admin', 'user'): role = 'user'
    db = get_db()
    try:
        db.execute('INSERT INTO users (username, password_hash, password_plain, display_name, khoi, bo_phan, chuc_vu, ma_nvkd_list, email, ma_bp, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   (username, hash_password(password), password, display_name, khoi, bo_phan, chuc_vu, ma_nvkd_list, email, ma_bp, role))
        db.commit()
        # Get new user id and assign dashboards
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
    if role not in ('admin', 'user'): role = 'user'
    db = get_db()
    if new_password:
        db.execute('UPDATE users SET display_name=?, khoi=?, bo_phan=?, chuc_vu=?, ma_nvkd_list=?, email=?, ma_bp=?, role=?, is_active=?, password_hash=?, password_plain=? WHERE id=?',
                    (display_name, khoi, bo_phan, chuc_vu, ma_nvkd_list, email, ma_bp, role, is_active, hash_password(new_password), new_password, user_id))
    else:
        db.execute('UPDATE users SET display_name=?, khoi=?, bo_phan=?, chuc_vu=?, ma_nvkd_list=?, email=?, ma_bp=?, role=?, is_active=? WHERE id=?',
                    (display_name, khoi, bo_phan, chuc_vu, ma_nvkd_list, email, ma_bp, role, is_active, user_id))
    db.commit()
    # Update dashboard permissions
    dash_ids = request.form.getlist('dash_ids')
    db.execute('DELETE FROM user_dashboards WHERE user_id=?', (user_id,))
    for did in dash_ids:
        try:
            db.execute('INSERT INTO user_dashboards (user_id, dashboard_id) VALUES (?, ?)', (user_id, int(did)))
        except Exception:
            pass
    db.commit()
    flash('Đã cập nhật user', 'success')
    return redirect(url_for('admin.admin_index') + '#users')


@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def user_delete(user_id):
    if user_id == session.get('user_id'):
        flash('Không thể xóa tài khoản đang đăng nhập', 'error')
        return redirect(url_for('admin.admin_index') + '#users')
    db = get_db()
    db.execute('DELETE FROM user_dashboards WHERE user_id = ?', (user_id,))
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    flash('Đã xóa user', 'success')
    return redirect(url_for('admin.admin_index') + '#users')


@bp.route('/dashboard/add', methods=['POST'])
@admin_required
def dashboard_add():
    name = request.form.get('name', '').strip()
    slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
    powerbi_url = request.form.get('powerbi_url', '').strip()
    description = request.form.get('description', '').strip()
    dashboard_type = request.form.get('dashboard_type', 'powerbi')
    sort_order = request.form.get('sort_order', 0, type=int)
    if not name or not slug:
        flash('Tên và slug không được để trống', 'error')
        return redirect(url_for('admin.admin_index') + '#dashboards')
    if dashboard_type == 'powerbi' and not powerbi_url:
        flash('Dashboard Power BI cần có URL', 'error')
        return redirect(url_for('admin.admin_index') + '#dashboards')
    db = get_db()
    try:
        db.execute('INSERT INTO dashboards (slug, name, powerbi_url, description, dashboard_type, sort_order) VALUES (?, ?, ?, ?, ?, ?)',
                   (slug, name, powerbi_url or '', description, dashboard_type, sort_order))
        db.commit()
        flash(f'Đã tạo dashboard "{name}"', 'success')
    except Exception as e:
        err = str(e).lower()
        if 'unique' in err or 'duplicate' in err:
            flash(f'Slug "{slug}" đã tồn tại', 'error')
        else:
            flash(f'Lỗi: {e}', 'error')
    return redirect(url_for('admin.admin_index') + '#dashboards')


@bp.route('/dashboard/<int:dash_id>/edit', methods=['POST'])
@admin_required
def dashboard_edit(dash_id):
    name = request.form.get('name', '').strip()
    slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
    powerbi_url = request.form.get('powerbi_url', '').strip()
    description = request.form.get('description', '').strip()
    dashboard_type = request.form.get('dashboard_type', 'powerbi')
    sort_order = request.form.get('sort_order', 0, type=int)
    is_active = 1 if request.form.get('is_active') else 0
    db = get_db()
    try:
        db.execute(f'''UPDATE dashboards SET name=?, slug=?, powerbi_url=?, description=?, dashboard_type=?, sort_order=?, is_active=?,
                      updated_at={sql_now()} WHERE id=?''',
                   (name, slug, powerbi_url or '', description, dashboard_type, sort_order, is_active, dash_id))
        db.commit()
        flash('Đã cập nhật dashboard', 'success')
    except Exception as e:
        err = str(e).lower()
        if 'unique' in err or 'duplicate' in err:
            flash(f'Slug "{slug}" đã tồn tại', 'error')
        else:
            flash(f'Lỗi: {e}', 'error')
    return redirect(url_for('admin.admin_index') + '#dashboards')


@bp.route('/dashboard/<int:dash_id>/delete', methods=['POST'])
@admin_required
def dashboard_delete(dash_id):
    db = get_db()
    db.execute('DELETE FROM user_dashboards WHERE dashboard_id = ?', (dash_id,))
    db.execute('DELETE FROM dashboards WHERE id = ?', (dash_id,))
    db.commit()
    flash('Đã xóa dashboard', 'success')
    return redirect(url_for('admin.admin_index') + '#dashboards')


@bp.route('/permissions/<int:dash_id>', methods=['GET', 'POST'])
@admin_required
def permissions(dash_id):
    db = get_db()
    dashboard = db.execute('SELECT * FROM dashboards WHERE id = ?', (dash_id,)).fetchone()
    if not dashboard: abort(404)
    if request.method == 'POST':
        db.execute('DELETE FROM user_dashboards WHERE dashboard_id = ?', (dash_id,))
        for uid in request.form.getlist('user_ids'):
            db.execute('INSERT INTO user_dashboards (user_id, dashboard_id) VALUES (?, ?)', (int(uid), dash_id))
        db.commit()
        flash(f'Đã cập nhật quyền cho "{dashboard["name"]}"', 'success')
        return redirect(url_for('admin.admin_index') + '#dashboards')
    users = db.execute("SELECT * FROM users WHERE role != 'admin' AND is_active = 1 ORDER BY username").fetchall()
    assigned = [r['user_id'] for r in db.execute('SELECT user_id FROM user_dashboards WHERE dashboard_id = ?', (dash_id,)).fetchall()]
    return render_template('admin_permissions.html', dashboard=dashboard, users=users, assigned=assigned,
        username=g.current_user['display_name'] or g.current_user['username'])


@bp.route('/user/<int:user_id>/permissions', methods=['POST'])
@admin_required
def user_permissions(user_id):
    """Phân quyền dashboard cho 1 user cụ thể"""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        abort(404)
    db.execute('DELETE FROM user_dashboards WHERE user_id = ?', (user_id,))
    for did in request.form.getlist('dash_ids'):
        db.execute('INSERT INTO user_dashboards (user_id, dashboard_id) VALUES (?, ?)', (user_id, int(did)))
    db.commit()
    flash(f'Đã cập nhật quyền cho "{user["display_name"] or user["username"]}"', 'success')
    return redirect(url_for('admin.admin_index') + '#users')


@bp.route('/user/<int:user_id>/bp', methods=['POST'])
@admin_required
def user_bp(user_id):
    """Cập nhật mã BP cho user (AJAX)"""
    from flask import jsonify as jf
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return jf({'ok': False}), 404
    ma_bp = request.json.get('ma_bp', '') if request.is_json else ''
    db.execute('UPDATE users SET ma_bp = ? WHERE id = ?', (ma_bp, user_id))
    db.commit()
    return jf({'ok': True})


# ==============================================================
# KỲ BÁO CÁO CRUD
# ==============================================================

def _parse_date_vn(s):
    """Chuyển dd/mm/yyyy → yyyy-mm-dd cho SQL"""
    s = s.strip()
    if not s:
        return None
    parts = s.split('/')
    if len(parts) == 3:
        return f'{parts[2]}-{parts[1]}-{parts[0]}'
    return s  # nếu đã ở dạng yyyy-mm-dd


def _format_date_vn(d):
    """Chuyển yyyy-mm-dd hoặc date object → dd/mm/yyyy"""
    if d is None:
        return ''
    s = str(d)[:10]
    if '-' in s:
        parts = s.split('-')
        return f'{parts[2]}/{parts[1]}/{parts[0]}'
    return s


@bp.route('/kbc/add', methods=['POST'])
@admin_required
def kbc_add():
    fields = ['ma_kbc', 'ten_kbc', 'loai_kbc', 'ngay_bd_xuat_ban', 'ngay_kt_xuat_ban',
              'ngay_bd_thu_tien', 'ngay_kt_thu_tien', 'ngay_bd_lan_ki', 'ngay_kt_lan_ki',
              'ngay_du_no_dau_ki', 'ngay_du_no_cuoi_ki']
    vals = {f: request.form.get(f, '').strip() for f in fields}
    for f in fields:
        if not vals[f]:
            flash(f'Trường {f} không được để trống', 'error')
            return redirect(url_for('admin.admin_index') + '#kbc')
    date_fields = [f for f in fields if f.startswith('ngay_')]
    for f in date_fields:
        vals[f] = _parse_date_vn(vals[f])
        if not vals[f]:
            flash(f'Ngày {f} không hợp lệ', 'error')
            return redirect(url_for('admin.admin_index') + '#kbc')
    db = get_db()
    try:
        db.execute('''INSERT INTO ky_bao_cao (ma_kbc, ten_kbc, loai_kbc, ngay_bd_xuat_ban, ngay_kt_xuat_ban,
            ngay_bd_thu_tien, ngay_kt_thu_tien, ngay_bd_lan_ki, ngay_kt_lan_ki, ngay_du_no_dau_ki, ngay_du_no_cuoi_ki)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (vals['ma_kbc'], vals['ten_kbc'], vals['loai_kbc'],
             vals['ngay_bd_xuat_ban'], vals['ngay_kt_xuat_ban'],
             vals['ngay_bd_thu_tien'], vals['ngay_kt_thu_tien'],
             vals['ngay_bd_lan_ki'], vals['ngay_kt_lan_ki'],
             vals['ngay_du_no_dau_ki'], vals['ngay_du_no_cuoi_ki']))
        db.commit()
        flash(f'Đã tạo kỳ "{vals["ten_kbc"]}"', 'success')
    except Exception as e:
        err = str(e).lower()
        if 'unique' in err or 'duplicate' in err:
            flash(f'Mã kỳ "{vals["ma_kbc"]}" đã tồn tại', 'error')
        else:
            flash(f'Lỗi: {e}', 'error')
    return redirect(url_for('admin.admin_index') + '#kbc')


@bp.route('/kbc/<int:kbc_id>/edit', methods=['POST'])
@admin_required
def kbc_edit(kbc_id):
    fields = ['ten_kbc', 'loai_kbc', 'ngay_bd_xuat_ban', 'ngay_kt_xuat_ban',
              'ngay_bd_thu_tien', 'ngay_kt_thu_tien', 'ngay_bd_lan_ki', 'ngay_kt_lan_ki',
              'ngay_du_no_dau_ki', 'ngay_du_no_cuoi_ki']
    vals = {f: request.form.get(f, '').strip() for f in fields}
    for f in fields:
        if not vals[f]:
            flash(f'Trường {f} không được để trống', 'error')
            return redirect(url_for('admin.admin_index') + '#kbc')
    date_fields = [f for f in fields if f.startswith('ngay_')]
    for f in date_fields:
        vals[f] = _parse_date_vn(vals[f])
        if not vals[f]:
            flash(f'Ngày {f} không hợp lệ', 'error')
            return redirect(url_for('admin.admin_index') + '#kbc')
    db = get_db()
    db.execute('''UPDATE ky_bao_cao SET ten_kbc=?, loai_kbc=?, ngay_bd_xuat_ban=?, ngay_kt_xuat_ban=?,
        ngay_bd_thu_tien=?, ngay_kt_thu_tien=?, ngay_bd_lan_ki=?, ngay_kt_lan_ki=?,
        ngay_du_no_dau_ki=?, ngay_du_no_cuoi_ki=? WHERE id=?''',
        (vals['ten_kbc'], vals['loai_kbc'],
         vals['ngay_bd_xuat_ban'], vals['ngay_kt_xuat_ban'],
         vals['ngay_bd_thu_tien'], vals['ngay_kt_thu_tien'],
         vals['ngay_bd_lan_ki'], vals['ngay_kt_lan_ki'],
         vals['ngay_du_no_dau_ki'], vals['ngay_du_no_cuoi_ki'], kbc_id))
    db.commit()
    flash('Đã cập nhật kỳ báo cáo', 'success')
    return redirect(url_for('admin.admin_index') + '#kbc')


@bp.route('/kbc/<int:kbc_id>/delete', methods=['POST'])
@admin_required
def kbc_delete(kbc_id):
    db = get_db()
    db.execute('DELETE FROM ky_bao_cao WHERE id = ?', (kbc_id,))
    db.commit()
    flash('Đã xóa kỳ báo cáo', 'success')
    return redirect(url_for('admin.admin_index') + '#kbc')