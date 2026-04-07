"""admin/permissions.py — Permission matrix APIs, user permissions, user BP"""
import json
from flask import request, redirect, url_for, flash, abort, g, render_template
from database import get_db
from auth import admin_required
from admin import bp, _admin_bp_list, _filter_users_by_bp, _can_manage_user, _log_audit


@bp.route('/permissions/<int:dash_id>', methods=['GET', 'POST'])
@admin_required
def permissions(dash_id):
    db = get_db()
    dashboard = db.execute('SELECT * FROM dashboards WHERE id = ?', (dash_id,)).fetchone()
    if not dashboard:
        abort(404)
    admin_bps = _admin_bp_list()
    if request.method == 'POST':
        all_users = db.execute("SELECT * FROM users WHERE role != 'admin' AND is_active = 1 ORDER BY username").fetchall()
        managed = _filter_users_by_bp(all_users, admin_bps)
        managed_ids = set(u['id'] for u in managed)
        for uid in managed_ids:
            db.execute('DELETE FROM user_dashboards WHERE dashboard_id = ? AND user_id = ?', (dash_id, uid))
        for uid in request.form.getlist('user_ids'):
            uid = int(uid)
            if uid in managed_ids:
                db.execute('INSERT INTO user_dashboards (user_id, dashboard_id) VALUES (?, ?)', (uid, dash_id))
        db.commit()
        flash(f'Đã cập nhật quyền cho "{dashboard["name"]}"', 'success')
        return redirect(url_for('admin.admin_index') + '#dashboards')
    all_users = db.execute("SELECT * FROM users WHERE role != 'admin' AND is_active = 1 ORDER BY username").fetchall()
    users = _filter_users_by_bp(all_users, admin_bps)
    assigned = [r['user_id'] for r in db.execute('SELECT user_id FROM user_dashboards WHERE dashboard_id = ?', (dash_id,)).fetchall()]
    return render_template('admin_permissions.html', dashboard=dashboard, users=users, assigned=assigned,
        username=g.current_user['display_name'] or g.current_user['username'])


@bp.route('/user/<int:user_id>/permissions', methods=['POST'])
@admin_required
def user_permissions(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        abort(404)
    admin_bps = _admin_bp_list()
    if not _can_manage_user(admin_bps, user):
        flash('Bạn không có quyền chỉnh sửa user này', 'error')
        return redirect(url_for('admin.admin_index') + '#users')
    db.execute('DELETE FROM user_dashboards WHERE user_id = ?', (user_id,))
    new_dids = request.form.getlist('dash_ids')
    for did in new_dids:
        db.execute('INSERT INTO user_dashboards (user_id, dashboard_id) VALUES (?, ?)', (user_id, int(did)))
    db.commit()
    _log_audit('perm_change', user_id, user['username'], {'dash_ids': new_dids})
    flash(f'Đã cập nhật quyền cho "{user["display_name"] or user["username"]}"', 'success')
    return redirect(url_for('admin.admin_index') + '#users')


@bp.route('/user/<int:user_id>/bp', methods=['POST'])
@admin_required
def user_bp(user_id):
    from flask import jsonify as jf
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return jf({'ok': False}), 404
    admin_bps = _admin_bp_list()
    if not _can_manage_user(admin_bps, user):
        return jf({'ok': False, 'error': 'Không có quyền'}), 403
    ma_bp = request.json.get('ma_bp', '') if request.is_json else ''
    if admin_bps and ma_bp:
        new_bps = set(b.strip() for b in ma_bp.split(',') if b.strip())
        if not new_bps.issubset(set(admin_bps)):
            return jf({'ok': False, 'error': 'BP ngoài phạm vi'}), 403
    old_bp = user['ma_bp'] or ''
    db.execute('UPDATE users SET ma_bp = ? WHERE id = ?', (ma_bp, user_id))
    db.commit()
    if old_bp != ma_bp:
        _log_audit('bp_change', user_id, user['username'], {'ma_bp': {'old': old_bp, 'new': ma_bp}})
    return jf({'ok': True})


@bp.route('/phan-quyen/toggle', methods=['POST'])
@admin_required
def perm_toggle():
    data = request.get_json(force=True)
    user_id = data.get('user_id')
    dash_id = data.get('dashboard_id')
    action = data.get('action')
    if not user_id or not dash_id:
        return json.dumps({'ok': False}), 400
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    admin_bps = _admin_bp_list()
    if user and not _can_manage_user(admin_bps, user):
        return json.dumps({'ok': False, 'error': 'Không có quyền'}), 403
    if action == 'add':
        try:
            db.execute('INSERT INTO user_dashboards (user_id, dashboard_id) VALUES (?, ?)', (user_id, dash_id))
        except:
            pass
    else:
        db.execute('DELETE FROM user_dashboards WHERE user_id=? AND dashboard_id=?', (user_id, dash_id))
    db.commit()
    return json.dumps({'ok': True})


@bp.route('/phan-quyen/bulk', methods=['POST'])
@admin_required
def perm_bulk():
    data = request.get_json(force=True)
    mode = data.get('mode')
    target_id = data.get('target_id')
    ids = data.get('ids', [])
    db = get_db()
    admin_bps = _admin_bp_list()
    if mode == 'dash_col':
        all_users = db.execute('SELECT * FROM users').fetchall()
        managed_ids = set(u['id'] for u in _filter_users_by_bp(all_users, admin_bps))
        for uid in managed_ids:
            db.execute('DELETE FROM user_dashboards WHERE dashboard_id=? AND user_id=?', (target_id, uid))
        for uid in ids:
            uid = int(uid)
            if uid in managed_ids:
                try:
                    db.execute('INSERT INTO user_dashboards (user_id, dashboard_id) VALUES (?, ?)', (uid, target_id))
                except:
                    pass
    db.commit()
    return json.dumps({'ok': True})