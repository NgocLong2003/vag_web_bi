"""admin/kbc.py — Kỳ báo cáo CRUD (hierarchical with parent_id)"""
from flask import request, redirect, url_for, flash
from database import get_db
from auth import admin_required
from admin import bp, _parse_date_vn


@bp.route('/kbc/add', methods=['POST'])
@admin_required
def kbc_add():
    db = get_db()
    ma_kbc = request.form.get('ma_kbc', '').strip()
    ten_kbc = request.form.get('ten_kbc', '').strip()
    loai_kbc = request.form.get('loai_kbc', '').strip()
    parent_id = request.form.get('parent_id', '').strip()
    sort_order = request.form.get('sort_order', '0').strip()

    if not ma_kbc or not ten_kbc or not loai_kbc:
        flash('Mã, tên và loại không được để trống', 'error')
        return redirect(url_for('admin.admin_index') + '#kbc')

    date_fields = ['ngay_bd_xuat_ban', 'ngay_kt_xuat_ban', 'ngay_bd_thu_tien', 'ngay_kt_thu_tien',
                   'ngay_bd_lan_ki', 'ngay_kt_lan_ki', 'ngay_du_no_dau_ki', 'ngay_du_no_cuoi_ki']
    vals = {}
    for f in date_fields:
        raw = request.form.get(f, '').strip()
        if raw:
            vals[f] = _parse_date_vn(raw)
        else:
            if loai_kbc == 'Tháng':
                flash(f'Kỳ Tháng: trường {f} không được để trống', 'error')
                return redirect(url_for('admin.admin_index') + '#kbc')
            vals[f] = None

    pid = int(parent_id) if parent_id else None
    sord = int(sort_order) if sort_order else 0

    try:
        db.execute('''INSERT INTO ky_bao_cao (ma_kbc, ten_kbc, loai_kbc, parent_id, sort_order,
            ngay_bd_xuat_ban, ngay_kt_xuat_ban, ngay_bd_thu_tien, ngay_kt_thu_tien,
            ngay_bd_lan_ki, ngay_kt_lan_ki, ngay_du_no_dau_ki, ngay_du_no_cuoi_ki)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (ma_kbc, ten_kbc, loai_kbc, pid, sord,
             vals['ngay_bd_xuat_ban'], vals['ngay_kt_xuat_ban'],
             vals['ngay_bd_thu_tien'], vals['ngay_kt_thu_tien'],
             vals['ngay_bd_lan_ki'], vals['ngay_kt_lan_ki'],
             vals['ngay_du_no_dau_ki'], vals['ngay_du_no_cuoi_ki']))
        db.commit()
        flash(f'Đã tạo kỳ "{ten_kbc}"', 'success')
    except Exception as e:
        err = str(e).lower()
        if 'unique' in err or 'duplicate' in err:
            flash(f'Mã kỳ "{ma_kbc}" đã tồn tại', 'error')
        else:
            flash(f'Lỗi: {e}', 'error')
    return redirect(url_for('admin.admin_index') + '#kbc')


@bp.route('/kbc/<int:kbc_id>/edit', methods=['POST'])
@admin_required
def kbc_edit(kbc_id):
    db = get_db()
    ten_kbc = request.form.get('ten_kbc', '').strip()
    loai_kbc = request.form.get('loai_kbc', '').strip()
    parent_id = request.form.get('parent_id', '').strip()
    sort_order = request.form.get('sort_order', '0').strip()

    if not ten_kbc or not loai_kbc:
        flash('Tên và loại không được để trống', 'error')
        return redirect(url_for('admin.admin_index') + '#kbc')

    date_fields = ['ngay_bd_xuat_ban', 'ngay_kt_xuat_ban', 'ngay_bd_thu_tien', 'ngay_kt_thu_tien',
                   'ngay_bd_lan_ki', 'ngay_kt_lan_ki', 'ngay_du_no_dau_ki', 'ngay_du_no_cuoi_ki']
    vals = {}
    for f in date_fields:
        raw = request.form.get(f, '').strip()
        if raw:
            vals[f] = _parse_date_vn(raw)
        else:
            if loai_kbc == 'Tháng':
                flash(f'Kỳ Tháng: trường {f} không được để trống', 'error')
                return redirect(url_for('admin.admin_index') + '#kbc')
            vals[f] = None

    pid = int(parent_id) if parent_id else None
    sord = int(sort_order) if sort_order else 0

    db.execute('''UPDATE ky_bao_cao SET ten_kbc=?, loai_kbc=?, parent_id=?, sort_order=?,
        ngay_bd_xuat_ban=?, ngay_kt_xuat_ban=?, ngay_bd_thu_tien=?, ngay_kt_thu_tien=?,
        ngay_bd_lan_ki=?, ngay_kt_lan_ki=?, ngay_du_no_dau_ki=?, ngay_du_no_cuoi_ki=? WHERE id=?''',
        (ten_kbc, loai_kbc, pid, sord,
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