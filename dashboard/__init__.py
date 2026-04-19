import base64
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, abort, g
from database import get_db, log_activity, sql_now
from auth import login_required, admin_required

bp = Blueprint('dashboard', __name__)


def _get_user_dashboards(user):
    """Lấy danh sách dashboard user có quyền xem.
    Logic: admin = tất cả, user = manual (user_dashboards) UNION auto (by khoi)."""
    db = get_db()
    if user['role'] == 'admin':
        return db.execute('SELECT * FROM dashboards WHERE is_active = 1 ORDER BY category, sort_order, name').fetchall()

    # Manual: assigned in user_dashboards
    manual = db.execute('''
        SELECT d.* FROM dashboards d JOIN user_dashboards ud ON d.id = ud.dashboard_id
        WHERE ud.user_id = ? AND d.is_active = 1
    ''', (user['id'],)).fetchall()

    # Auto: by khoi (user.khoi matches dashboard.category)
    user_khoi = (user.get('khoi') or '').strip() if 'khoi' in user.keys() else ''
    if user_khoi:
        auto = db.execute(
            'SELECT * FROM dashboards WHERE is_active = 1 AND category = ?',
            (user_khoi,)
        ).fetchall()
    else:
        auto = []

    # Union + deduplicate by id, maintain order
    seen_ids = set()
    result = []
    for row in list(manual) + list(auto):
        rid = row['id']
        if rid not in seen_ids:
            seen_ids.add(rid)
            result.append(row)
    result.sort(key=lambda d: (d.get('category') or '', d.get('sort_order') or 0, d.get('name') or ''))
    return result


def _group_dashboards(dashboards):
    """Group dashboards by category for sidebar/dashboard_list display."""
    groups = {}
    for d in dashboards:
        cat = (d.get('category') or '').strip() or 'Khác'
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(d)
    return groups


def _user_can_view(user, dashboard_id):
    """Kiểm tra user có quyền xem dashboard không (manual hoặc auto by khoi)."""
    if user['role'] == 'admin':
        return True
    db = get_db()
    # Manual check
    if db.execute('SELECT 1 FROM user_dashboards WHERE user_id=? AND dashboard_id=?',
                  (user['id'], dashboard_id)).fetchone():
        return True
    # Auto check by khoi
    user_khoi = (user.get('khoi') or '').strip() if 'khoi' in user.keys() else ''
    if user_khoi:
        dash = db.execute('SELECT category FROM dashboards WHERE id=? AND is_active=1', (dashboard_id,)).fetchone()
        if dash and (dash['category'] or '').strip() == user_khoi:
            return True
    return False


def _row_columns(row):
    """Lấy danh sách tên cột từ pyodbc Row hoặc sqlite3.Row."""
    try:
        # pyodbc Row
        return [desc[0] for desc in row.cursor_description]
    except AttributeError:
        pass
    try:
        # sqlite3.Row
        return list(row.keys())
    except:
        return []


def _safe_get(row, col, available_cols, default=''):
    """Đọc giá trị cột an toàn — tương thích cả pyodbc lẫn sqlite3."""
    if available_cols and col not in available_cols:
        return default
    try:
        val = row[col]
        return val if val is not None else default
    except:
        return default


# ═══════════════════════════════════════════════════════════════
# ROUTES: Dashboard list & view (Flask HTML — giữ nguyên)
# ═══════════════════════════════════════════════════════════════

@bp.route('/dashboards')
@login_required
def dashboard_list():
    dashboards = _get_user_dashboards(g.current_user)
    if len(dashboards) == 1:
        return redirect(url_for('dashboard.dashboard_view', slug=dashboards[0]['slug']))
    grouped = _group_dashboards(dashboards)
    return render_template('dashboard_list.html', dashboards=dashboards,
        grouped_dashboards=grouped,
        username=g.current_user['display_name'] or g.current_user['username'],
        role=g.current_user['role'])


@bp.route('/d/<slug>')
@login_required
def dashboard_view(slug):
    db = get_db()
    user = g.current_user
    dashboard = db.execute('SELECT * FROM dashboards WHERE slug = ? AND is_active = 1', (slug,)).fetchone()
    if not dashboard:
        abort(404)

    # Kiểm tra quyền (manual + auto by khoi)
    if not _user_can_view(user, dashboard['id']):
        abort(403)

    all_dashboards = _get_user_dashboards(user)
    grouped = _group_dashboards(all_dashboards)
    dash_type = dashboard['dashboard_type'] if 'dashboard_type' in dashboard.keys() else 'powerbi'

    # Chọn template theo loại dashboard
    tpl_vars = dict(
        username=user['display_name'] or user['username'],
        dashboard_name=dashboard['name'],
        dashboard_slug=slug,
        role=user['role'],
        all_dashboards=all_dashboards,
        user_ma_nvkd=(user['ma_nvkd_list'] or '') if 'ma_nvkd_list' in user.keys() else '',
        user_ma_bp=(user['ma_bp'] or '') if 'ma_bp' in user.keys() else '',
        # Sidebar context
        dashboards=all_dashboards,
        grouped_dashboards=grouped,
        current_slug=slug,
        user=dict(user),
    )

    if dash_type == 'analytics':
        return render_template('analytics.html', **tpl_vars)

    if dash_type == 'report':
        from reports import get_report
        report = get_report(slug)
        if report:
            return render_template(report['template'], **tpl_vars)
        abort(404)

    # Mặc định: Power BI dashboard
    return render_template('dashboard.html', **tpl_vars)


@bp.route('/api/report-url', methods=['POST'])
@login_required
def get_report_url():
    token = request.json.get('token', '') if request.is_json else ''
    if token != session.get('token', ''):
        abort(403)
    slug = request.json.get('slug', '') if request.is_json else ''
    db = get_db()
    user = g.current_user
    dashboard = db.execute('SELECT * FROM dashboards WHERE slug = ? AND is_active = 1', (slug,)).fetchone()
    if not dashboard:
        abort(404)
    if user['role'] != 'admin':
        if not db.execute('SELECT 1 FROM user_dashboards WHERE user_id=? AND dashboard_id=?',
                          (user['id'], dashboard['id'])).fetchone():
            abort(403)
    url = dashboard['powerbi_url']
    log_activity(user['id'], 'view_dashboard', dashboard['id'])
    s1 = base64.b64encode(url.encode()).decode()
    s2 = s1[::-1]
    s3 = base64.b64encode(s2.encode()).decode()
    return jsonify({'d': s3})

@bp.route('/api/admin/me')
@admin_required
def api_admin_me():
    """Trả thông tin phân quyền admin của user đang đăng nhập"""
    db = get_db()
    user = g.current_user
 
    # Lấy tất cả quyền của user
    perms = db.execute('''
        SELECT ap.*, atg.name AS group_name, atg.tabs AS group_tabs,
               atg.scope_category AS group_scope_category
        FROM admin_permissions ap
        LEFT JOIN admin_tab_groups atg ON ap.tab_group_id = atg.id
        WHERE ap.user_id = ? AND ap.is_active = 1
    ''', (user['id'],)).fetchall()
 
    if not perms:
        # Admin không có dòng nào trong admin_permissions → coi như department, scope theo khối
        user_khoi = (user.get('khoi') or '').strip() if 'khoi' in user.keys() else ''
        return jsonify({
            'success': True,
            'admin_level': 'department',
            'is_super': False,
            'scopes': [{
                'scope_type': 'khoi' if user_khoi else 'all',
                'scope_value': user_khoi,
                'tab_group_id': None,
                'group_name': None,
                'group_tabs': None,
                'can_create': True,
                'can_edit': True,
                'can_delete': False,
            }],
            'allowed_tabs': ['dashboards', 'users', 'permissions', 'log'],
            'tab_groups': [],
        })
 
    is_super = any(p['admin_level'] == 'super' for p in perms)
 
    scopes = []
    allowed_extra_tabs = set()
    for p in perms:
        scope = {
            'scope_type': p['scope_type'],
            'scope_value': p['scope_value'] or '',
            'tab_group_id': p['tab_group_id'],
            'group_name': p['group_name'] if 'group_name' in p.keys() else None,
            'group_tabs': p['group_tabs'] if 'group_tabs' in p.keys() else None,
            'can_create': bool(p['can_create']),
            'can_edit': bool(p['can_edit']),
            'can_delete': bool(p['can_delete']),
        }
        scopes.append(scope)
        # Thu thập tab từ tab_groups
        if scope['group_tabs']:
            for t in scope['group_tabs'].split(','):
                allowed_extra_tabs.add(t.strip())
 
    # 4 tab chung luôn có
    base_tabs = ['dashboards', 'users', 'permissions', 'log']
 
    if is_super:
        # Super admin: thấy tất cả tab groups
        all_groups = db.execute('SELECT * FROM admin_tab_groups WHERE is_active = 1 ORDER BY sort_order').fetchall()
        for g_row in all_groups:
            for t in (g_row['tabs'] or '').split(','):
                allowed_extra_tabs.add(t.strip())
 
    allowed_tabs = base_tabs + sorted(allowed_extra_tabs)
 
    return jsonify({
        'success': True,
        'admin_level': 'super' if is_super else 'department',
        'is_super': is_super,
        'scopes': scopes,
        'allowed_tabs': allowed_tabs,
    })
 
 
@bp.route('/api/admin/tab-groups')
@admin_required
def api_admin_tab_groups():
    """Trả danh sách nhóm tab (chỉ super admin thấy tất cả)"""
    db = get_db()
    user = g.current_user
 
    rows = db.execute('SELECT * FROM admin_tab_groups WHERE is_active = 1 ORDER BY sort_order').fetchall()
 
    # Kiểm tra user có phải super admin không
    is_super = db.execute(
        "SELECT 1 FROM admin_permissions WHERE user_id = ? AND admin_level = 'super' AND is_active = 1",
        (user['id'],)
    ).fetchone()
 
    if not is_super:
        # Chỉ trả tab groups mà user được gán
        user_group_ids = set()
        user_perms = db.execute(
            'SELECT tab_group_id FROM admin_permissions WHERE user_id = ? AND is_active = 1 AND tab_group_id IS NOT NULL',
            (user['id'],)
        ).fetchall()
        for p in user_perms:
            user_group_ids.add(p['tab_group_id'])
        rows = [r for r in rows if r['id'] in user_group_ids]
 
    data = []
    for r in rows:
        data.append({
            'id': r['id'],
            'name': r['name'],
            'description': r['description'] or '',
            'tabs': r['tabs'],
            'scope_category': r['scope_category'] or '',
            'sort_order': r['sort_order'] or 0,
        })
 
    return jsonify({'success': True, 'data': data})

# ═══════════════════════════════════════════════════════════════
# API: Dashboard list & update (JSON — cho React frontend)
# ═══════════════════════════════════════════════════════════════

@bp.route('/api/dashboards')
@login_required
def api_dashboards():
    """Trả danh sách dashboard user được phép xem (JSON cho React)"""
    user = g.current_user
    rows = _get_user_dashboards(user)

    # Xác định danh sách cột thực tế (tương thích pyodbc + sqlite3)
    if rows:
        cols = _row_columns(rows[0])
    else:
        cols = []

    data = []
    for d in rows:
        data.append({
            'id': d['id'],
            'slug': d['slug'],
            'name': d['name'],
            'description': _safe_get(d, 'description', cols),
            'dashboard_type': _safe_get(d, 'dashboard_type', cols, 'powerbi'),
            'powerbi_url': _safe_get(d, 'powerbi_url', cols),
            'sort_order': _safe_get(d, 'sort_order', cols, 0),
            'category': _safe_get(d, 'category', cols, ''),
            'icon_svg': _safe_get(d, 'icon_svg', cols),
            'color': _safe_get(d, 'color', cols, 'teal'),
            'update_mode': _safe_get(d, 'update_mode', cols, 'scheduled'),
            'update_interval': _safe_get(d, 'update_interval', cols),
            'updated_at': str(_safe_get(d, 'updated_at', cols)),
            'is_active': d['is_active'],
        })

    return jsonify({'success': True, 'data': data})


@bp.route('/api/dashboards/<int:dashboard_id>', methods=['POST'])
@admin_required
def api_dashboard_update(dashboard_id):
    """Cập nhật thông tin dashboard (JSON body, gọi từ React admin)"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Không có dữ liệu'}), 400

    db = get_db()
    dash = db.execute('SELECT id FROM dashboards WHERE id = ?', (dashboard_id,)).fetchone()
    if not dash:
        return jsonify({'success': False, 'error': 'Dashboard không tồn tại'}), 404

    allowed_fields = [
        'name', 'slug', 'description', 'category', 'dashboard_type',
        'powerbi_url', 'sort_order', 'icon_svg', 'color',
        'update_mode', 'update_interval', 'is_active'
    ]

    sets = []
    params = []
    for f in allowed_fields:
        if f in data:
            sets.append(f'{f} = ?')
            params.append(data[f])

    if not sets:
        return jsonify({'success': False, 'error': 'Không có gì để cập nhật'}), 400

    try:
        sql = f"UPDATE dashboards SET {', '.join(sets)}, updated_at = {sql_now()} WHERE id = ?"
        params.append(dashboard_id)
        db.execute(sql, params)
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        err = str(e).lower()
        if 'unique' in err or 'duplicate' in err:
            return jsonify({'success': False, 'error': 'Slug đã tồn tại'}), 400
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/dashboards/all')
@admin_required
def api_dashboards_all():
    """Trả TẤT CẢ dashboard (kể cả đã tắt) — chỉ admin dùng trong trang quản trị"""
    db = get_db()
    rows = db.execute('SELECT * FROM dashboards ORDER BY category, sort_order, name').fetchall()
 
    if rows:
        cols = _row_columns(rows[0])
    else:
        cols = []
 
    data = []
    for d in rows:
        data.append({
            'id': d['id'],
            'slug': d['slug'],
            'name': d['name'],
            'description': _safe_get(d, 'description', cols),
            'dashboard_type': _safe_get(d, 'dashboard_type', cols, 'powerbi'),
            'powerbi_url': _safe_get(d, 'powerbi_url', cols),
            'sort_order': _safe_get(d, 'sort_order', cols, 0),
            'category': _safe_get(d, 'category', cols, ''),
            'icon_svg': _safe_get(d, 'icon_svg', cols),
            'color': _safe_get(d, 'color', cols, 'teal'),
            'update_mode': _safe_get(d, 'update_mode', cols, 'scheduled'),
            'update_interval': _safe_get(d, 'update_interval', cols),
            'updated_at': str(_safe_get(d, 'updated_at', cols)),
            'is_active': d['is_active'],
        })
 
    return jsonify({'success': True, 'data': data})