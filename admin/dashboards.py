"""admin/dashboards.py — Dashboard CRUD"""
from flask import request, redirect, url_for, flash
from database import get_db, sql_now
from auth import admin_required
from admin import bp


@bp.route('/dashboard/add', methods=['POST'])
@admin_required
def dashboard_add():
    name = request.form.get('name', '').strip()
    slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
    powerbi_url = request.form.get('powerbi_url', '').strip()
    description = request.form.get('description', '').strip()
    dashboard_type = request.form.get('dashboard_type', 'powerbi')
    category = request.form.get('category', '').strip()
    sort_order = request.form.get('sort_order', 0, type=int)
    if not name or not slug:
        flash('Tên và slug không được để trống', 'error')
        return redirect(url_for('admin.admin_index') + '#dashboards')
    if dashboard_type == 'powerbi' and not powerbi_url:
        flash('Dashboard Power BI cần có URL', 'error')
        return redirect(url_for('admin.admin_index') + '#dashboards')
    db = get_db()
    try:
        db.execute('INSERT INTO dashboards (slug, name, powerbi_url, description, dashboard_type, sort_order, category) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (slug, name, powerbi_url or '', description, dashboard_type, sort_order, category))
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
    category = request.form.get('category', '').strip()
    sort_order = request.form.get('sort_order', 0, type=int)
    is_active = 1 if request.form.get('is_active') else 0
    db = get_db()
    try:
        db.execute(f'''UPDATE dashboards SET name=?, slug=?, powerbi_url=?, description=?, dashboard_type=?, sort_order=?, is_active=?, category=?,
                      updated_at={sql_now()} WHERE id=?''',
                   (name, slug, powerbi_url or '', description, dashboard_type, sort_order, is_active, category, dash_id))
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