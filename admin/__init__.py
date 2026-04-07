"""
admin/__init__.py — Blueprint core, helpers, main page route.
Sub-routes imported from: users, dashboards, kbc, permissions, audit.
"""
from flask import Blueprint, render_template, g
import json as _json
from database import get_db, hash_password, sql_now
from auth import admin_required

try:
    from config import DB_TYPE
except ImportError:
    DB_TYPE = 'sqlite'

bp = Blueprint('admin', __name__, url_prefix='/admin',
               template_folder='../templates/admin')


# ═══════════════════════════════════════════════
# SHARED HELPERS (used by all sub-modules)
# ═══════════════════════════════════════════════

_AUDIT_FIELDS = ['display_name', 'khoi', 'bo_phan', 'chuc_vu', 'ma_nvkd_list',
                 'email', 'ma_bp', 'role', 'is_active']


def _log_audit(action, target_user_id, target_username='', changes=None):
    try:
        db = get_db()
        admin = g.current_user
        db.execute(
            'INSERT INTO user_audit_log (target_user_id, target_username, changed_by_id, changed_by_username, action, changes) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (target_user_id, target_username, admin['id'], admin['username'], action,
             _json.dumps(changes or {}, ensure_ascii=False)))
        db.commit()
    except Exception as e:
        print(f'[AUDIT] Error: {e}')


def _diff_user(old_row, new_data):
    changes = {}
    for f in _AUDIT_FIELDS:
        try:
            old_val = str(old_row[f] or '')
        except:
            old_val = ''
        new_val = str(new_data.get(f, '') or '')
        if old_val != new_val:
            changes[f] = {'old': old_val, 'new': new_val}
    return changes


def _admin_bp_list():
    u = g.current_user
    try:
        raw = u['ma_bp']
    except (KeyError, TypeError):
        raw = None
    if not raw or not str(raw).strip():
        return []
    return [b.strip() for b in str(raw).split(',') if b.strip()]


def _filter_users_by_bp(users, admin_bps):
    if not admin_bps:
        return list(users)
    admin_set = set(admin_bps)
    result = []
    for u in users:
        try:
            raw = u['ma_bp'] or ''
        except:
            raw = ''
        user_bps = set(b.strip() for b in str(raw).split(',') if b.strip())
        if user_bps & admin_set:
            result.append(u)
    return result


def _can_manage_user(admin_bps, user_row):
    if not admin_bps:
        return True
    try:
        raw = user_row['ma_bp'] or ''
    except:
        raw = ''
    user_bps = set(b.strip() for b in str(raw).split(',') if b.strip())
    return bool(user_bps & set(admin_bps))


def _parse_date_vn(s):
    s = s.strip()
    if not s:
        return None
    parts = s.split('/')
    if len(parts) == 3:
        return f'{parts[2]}-{parts[1]}-{parts[0]}'
    return s


# ═══════════════════════════════════════════════
# MAIN PAGE
# ═══════════════════════════════════════════════

@bp.route('/')
@admin_required
def admin_index():
    db = get_db()
    admin_bps = _admin_bp_list()

    all_users = db.execute('SELECT * FROM users ORDER BY role DESC, username').fetchall()
    users = _filter_users_by_bp(all_users, admin_bps)

    dashboards = db.execute('SELECT * FROM dashboards ORDER BY sort_order, name').fetchall()
    dash_user_counts = {}
    for d in dashboards:
        dash_user_counts[d['id']] = db.execute(
            'SELECT COUNT(*) FROM user_dashboards WHERE dashboard_id = ?', (d['id'],)).fetchone()[0]
    user_dash_map = {}
    for u in users:
        rows = db.execute('SELECT dashboard_id FROM user_dashboards WHERE user_id = ?', (u['id'],)).fetchall()
        user_dash_map[u['id']] = [r['dashboard_id'] for r in rows]

    all_bp = []
    try:
        bp_rows = db.execute("SELECT DISTINCT ma_bp FROM DMKHACHHANG_VIEW WHERE ma_bp IS NOT NULL AND ma_bp != '' AND ma_bp != 'TN' ORDER BY ma_bp").fetchall()
        all_bp = [r['ma_bp'] for r in bp_rows]
    except:
        pass
    if admin_bps:
        all_bp = [b for b in all_bp if b in admin_bps]

    ky_bao_cao = []
    try:
        rows = db.execute('SELECT * FROM ky_bao_cao ORDER BY sort_order, ngay_bd_xuat_ban DESC').fetchall()
        for r in rows:
            d = dict(r) if isinstance(r, dict) else {k: r[k] for k in r.keys()}
            if d.get('sort_order') is None:
                d['sort_order'] = 0
            if d.get('parent_id') is None or d.get('parent_id') == 0:
                d['parent_id'] = None
            ky_bao_cao.append(d)
    except:
        pass

    perm_users = _filter_users_by_bp(
        db.execute(
            'SELECT id, username, display_name, ma_nvkd_list, ma_bp, role, is_active '
            'FROM users ORDER BY ma_bp, ma_nvkd_list, display_name'
        ).fetchall(),
        admin_bps
    )
    perm_map = {}
    for uid, dids in user_dash_map.items():
        perm_map[uid] = dids

    return render_template('admin/admin.html', users=users, dashboards=dashboards,
        dash_user_counts=dash_user_counts, user_dash_map=user_dash_map, all_bp=all_bp,
        ky_bao_cao=ky_bao_cao, perm_users=perm_users, perm_map=perm_map,
        admin_bps=admin_bps,
        username=g.current_user['display_name'] or g.current_user['username'])


# ═══════════════════════════════════════════════
# IMPORT SUB-ROUTES (must be after bp is defined)
# ═══════════════════════════════════════════════
from admin import users, dashboards, kbc, permissions, audit, kpi