"""admin/audit.py — Audit log API endpoint"""
import json
from flask import request
from database import get_db
from auth import admin_required
from admin import bp, _admin_bp_list, _can_manage_user

try:
    from config import DB_TYPE
except ImportError:
    DB_TYPE = 'sqlite'


@bp.route('/audit-log')
@admin_required
def audit_log_api():
    db = get_db()
    days = request.args.get('days', '30')
    q = request.args.get('q', '').strip().lower()
    action = request.args.get('action', '').strip()
    user_id = request.args.get('user_id', '').strip()
    admin_bps = _admin_bp_list()

    conditions, params = [], []
    if user_id:
        conditions.append('target_user_id = ?')
        params.append(int(user_id))
    if action:
        conditions.append('action = ?')
        params.append(action)
    if days and days != '0':
        if DB_TYPE == 'sqlserver':
            conditions.append('created_at >= DATEADD(DAY, -CAST(? AS INT), GETDATE())')
        else:
            conditions.append("created_at >= datetime('now','localtime',?)")
        params.append(int(days) if DB_TYPE == 'sqlserver' else f'-{days} days')
    if q:
        conditions.append('(LOWER(target_username) LIKE ? OR LOWER(changed_by_username) LIKE ?)')
        params.extend([f'%{q}%', f'%{q}%'])

    where = (' WHERE ' + ' AND '.join(conditions)) if conditions else ''

    try:
        rows = db.execute(
            f'SELECT * FROM user_audit_log{where} ORDER BY created_at DESC',
            params
        ).fetchall()
    except Exception as e:
        return json.dumps({'ok': False, 'error': f'Query error: {e}'}), 500

    data = []
    for r in rows:
        if admin_bps:
            target_uid = r['target_user_id']
            target_user = db.execute('SELECT ma_bp FROM users WHERE id = ?', (target_uid,)).fetchone()
            if target_user and not _can_manage_user(admin_bps, target_user):
                continue

        data.append({
            'id': r['id'],
            'target_user_id': r['target_user_id'],
            'target_username': r['target_username'] or '',
            'changed_by_id': r['changed_by_id'],
            'changed_by_username': r['changed_by_username'] or '',
            'action': r['action'] or '',
            'changes': r['changes'] or '',
            'created_at': str(r['created_at'] or '')[:19]
        })

    return json.dumps({'ok': True, 'data': data[:500]})