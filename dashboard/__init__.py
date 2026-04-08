import base64
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, abort, g
from database import get_db, log_activity
from auth import login_required

bp = Blueprint('dashboard', __name__)


def _get_user_dashboards(user):
    """Lấy danh sách dashboard user có quyền xem"""
    db = get_db()
    if user['role'] == 'admin':
        return db.execute('SELECT * FROM dashboards WHERE is_active = 1 ORDER BY sort_order, name').fetchall()
    return db.execute('''
        SELECT d.* FROM dashboards d JOIN user_dashboards ud ON d.id = ud.dashboard_id
        WHERE ud.user_id = ? AND d.is_active = 1 ORDER BY d.sort_order, d.name
    ''', (user['id'],)).fetchall()


@bp.route('/dashboards')
@login_required
def dashboard_list():
    dashboards = _get_user_dashboards(g.current_user)
    if len(dashboards) == 1:
        return redirect(url_for('dashboard.dashboard_view', slug=dashboards[0]['slug']))
    return render_template('dashboard_list.html', dashboards=dashboards,
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

    # Kiểm tra quyền
    if user['role'] != 'admin':
        if not db.execute('SELECT 1 FROM user_dashboards WHERE user_id=? AND dashboard_id=?',
                          (user['id'], dashboard['id'])).fetchone():
            abort(403)

    all_dashboards = _get_user_dashboards(user)
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