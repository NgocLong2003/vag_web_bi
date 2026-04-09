import base64
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, abort, g
from database import get_db, log_activity
from auth import login_required

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