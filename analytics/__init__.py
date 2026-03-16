from flask import Blueprint, request, jsonify, g
from database import get_db, sql_date_ago, sql_date_ago_param, sql_extract_date, sql_extract_hour, sql_limit
from auth import login_required

bp = Blueprint('analytics', __name__)


@bp.route('/api/analytics/summary')
@login_required
def api_summary():
    db = get_db()
    days = request.args.get('days', 30, type=int)
    khoi_filter = request.args.get('khoi', '')
    bp_filter = request.args.get('bo_phan', '')

    date_cond = sql_date_ago()
    base_where = f"al.action='view_dashboard' AND {date_cond}"
    params = [sql_date_ago_param(days)]
    if khoi_filter:
        base_where += " AND u.khoi = ?"; params.append(khoi_filter)
    if bp_filter:
        base_where += " AND u.bo_phan = ?"; params.append(bp_filter)

    total_views = db.execute(f'SELECT COUNT(*) FROM activity_log al JOIN users u ON al.user_id=u.id WHERE {base_where}', params).fetchone()[0]
    active_users = db.execute(f'SELECT COUNT(DISTINCT al.user_id) FROM activity_log al JOIN users u ON al.user_id=u.id WHERE {base_where}', params).fetchone()[0]

    login_where = base_where.replace("al.action='view_dashboard'", "al.action='login'")
    total_logins = db.execute(f'SELECT COUNT(*) FROM activity_log al JOIN users u ON al.user_id=u.id WHERE {login_where}', params).fetchone()[0]

    tp, ts = sql_limit(10)
    top_dashboards = db.execute(f'SELECT {tp} d.name, COUNT(*) as views FROM activity_log al JOIN dashboards d ON al.dashboard_id=d.id JOIN users u ON al.user_id=u.id WHERE {base_where} GROUP BY d.name ORDER BY views DESC {ts}', params).fetchall()
    top_users = db.execute(f'SELECT {tp} u.display_name, u.username, u.khoi, u.bo_phan, COUNT(*) as views FROM activity_log al JOIN users u ON al.user_id=u.id WHERE {base_where} GROUP BY u.display_name, u.username, u.khoi, u.bo_phan ORDER BY views DESC {ts}', params).fetchall()

    ed = sql_extract_date()
    daily_views = db.execute(f'SELECT {ed} as day, COUNT(*) as views FROM activity_log al JOIN users u ON al.user_id=u.id WHERE {base_where} GROUP BY {ed} ORDER BY day', params).fetchall()
    eh = sql_extract_hour()
    hourly_views = db.execute(f'SELECT {eh} as hour, COUNT(*) as views FROM activity_log al JOIN users u ON al.user_id=u.id WHERE {base_where} GROUP BY {eh} ORDER BY hour', params).fetchall()

    by_khoi = db.execute(f"SELECT COALESCE(NULLIF(u.khoi,''),'(Chưa phân khối)') as khoi, COUNT(*) as views FROM activity_log al JOIN users u ON al.user_id=u.id WHERE {base_where} GROUP BY COALESCE(NULLIF(u.khoi,''),'(Chưa phân khối)') ORDER BY views DESC", params).fetchall()
    by_bo_phan = db.execute(f"SELECT COALESCE(NULLIF(u.bo_phan,''),'(Chưa phân BP)') as bo_phan, COUNT(*) as views FROM activity_log al JOIN users u ON al.user_id=u.id WHERE {base_where} GROUP BY COALESCE(NULLIF(u.bo_phan,''),'(Chưa phân BP)') ORDER BY views DESC", params).fetchall()

    all_khoi = [r[0] for r in db.execute("SELECT DISTINCT khoi FROM users WHERE khoi != '' ORDER BY khoi").fetchall()]
    all_bo_phan = [r[0] for r in db.execute("SELECT DISTINCT bo_phan FROM users WHERE bo_phan != '' ORDER BY bo_phan").fetchall()]

    rw = "1=1"; rp = []
    if khoi_filter: rw += " AND u.khoi = ?"; rp.append(khoi_filter)
    if bp_filter: rw += " AND u.bo_phan = ?"; rp.append(bp_filter)
    r_pre, r_suf = sql_limit(50)
    recent = db.execute(f'SELECT {r_pre} u.display_name, u.username, u.khoi, u.bo_phan, al.action, d.name as dash_name, al.created_at, al.ip FROM activity_log al JOIN users u ON al.user_id=u.id LEFT JOIN dashboards d ON al.dashboard_id=d.id WHERE {rw} ORDER BY al.created_at DESC {r_suf}', rp).fetchall()

    return jsonify({
        'total_views': total_views, 'active_users': active_users, 'total_logins': total_logins,
        'top_dashboards': [{'name': r['name'], 'views': r['views']} for r in top_dashboards],
        'top_users': [{'name': r['display_name'] or r['username'], 'views': r['views'], 'khoi': r['khoi'] or '', 'bo_phan': r['bo_phan'] or ''} for r in top_users],
        'daily_views': [{'day': str(r['day']), 'views': r['views']} for r in daily_views],
        'hourly_views': [{'hour': r['hour'], 'views': r['views']} for r in hourly_views],
        'by_khoi': [{'name': r['khoi'], 'views': r['views']} for r in by_khoi],
        'by_bo_phan': [{'name': r['bo_phan'], 'views': r['views']} for r in by_bo_phan],
        'filters': {'all_khoi': all_khoi, 'all_bo_phan': all_bo_phan},
        'recent': [{'user': r['display_name'] or r['username'], 'khoi': r['khoi'] or '', 'bo_phan': r['bo_phan'] or '',
                    'action': r['action'], 'dashboard': r['dash_name'] or '', 'time': str(r['created_at']), 'ip': r['ip']} for r in recent]
    })