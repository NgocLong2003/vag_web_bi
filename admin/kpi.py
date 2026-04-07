"""admin/kpi.py — KPI management: phân công + KPI targets (SQL Server)"""
import json
from flask import request, jsonify
from database import get_db
from auth import admin_required
from admin import bp

try:
    from config import SQLSERVER_CONFIG, DB_TYPE
except ImportError:
    SQLSERVER_CONFIG = None
    DB_TYPE = 'sqlite'


def _ss_conn():
    """Get direct SQL Server connection for kpi_targets (lives on SQL Server)."""
    import pyodbc
    c = SQLSERVER_CONFIG
    return pyodbc.connect(
        f"DRIVER={{{c['driver']}}};SERVER={c['server']},{c['port']};"
        f"DATABASE={c['database']};UID={c['username']};PWD={c['password']};"
        "TrustServerCertificate=yes;Connect Timeout=30;",
        autocommit=False
    )


def _recalc_paths(conn, ma_kbc):
    """Recalc stt_nhom for all rows in a period."""
    cur = conn.cursor()
    cur.execute('SELECT ma_nvkd, ma_ql, ma_bp FROM kpi_targets WHERE ma_kbc = ?', (ma_kbc,))
    rows = cur.fetchall()
    by_key = {}
    for r in rows:
        by_key[r[0]] = {'ma_ql': r[1] or '', 'ma_bp': r[2] or ''}

    for ma in by_key:
        path = []
        cur_ma = ma
        visited = set()
        while cur_ma and cur_ma in by_key and cur_ma not in visited:
            path.append(cur_ma)
            visited.add(cur_ma)
            cur_ma = by_key[cur_ma]['ma_ql']
        path.reverse()
        bp_code = by_key[ma]['ma_bp']
        stt = 'VAG.' + bp_code + '00.' + '.'.join(path) if path else ''
        cur.execute('UPDATE kpi_targets SET stt_nhom = ?, ldate = GETDATE() WHERE ma_kbc = ? AND ma_nvkd = ?',
                    (stt, ma_kbc, ma))
    conn.commit()


def _parse_kbc(ma_kbc):
    """Parse T01-2026 → (2026, 1)"""
    try:
        parts = ma_kbc.replace('T', '').split('-')
        return int(parts[1]), int(parts[0])
    except:
        return 2026, 1


# ═══════════════════════════════════════════════
# API: Load data
# ═══════════════════════════════════════════════

@bp.route('/kpi/data')
@admin_required
def kpi_data():
    """Load KPI: nhận 1 hoặc nhiều ma_kbc, SUM cross-period, trả detail breakdown."""
    ma_kbc_list = request.args.getlist('ma_kbc')
    ma_bp = request.args.get('ma_bp', '').strip()

    kbcs = []
    for k in ma_kbc_list:
        for part in k.split(','):
            part = part.strip()
            if part:
                kbcs.append(part)

    if not kbcs:
        return jsonify({'ok': True, 'assignments': [], 'kpi': {}, 'detail': {}})

    try:
        conn = _ss_conn()
        cur = conn.cursor()
        ph = ','.join(['?'] * len(kbcs))
        sql = f'''SELECT ma_kbc, ma_nvkd, ten_nvkd, ma_ql, ma_bp, stt_nhom,
                         kpi, kpi_cong_ty, kpi_ds, kpi_ds_cong_ty
                  FROM kpi_targets WHERE ma_kbc IN ({ph})'''
        params = list(kbcs)
        if ma_bp:
            sql += ' AND ma_bp = ?'
            params.append(ma_bp)
        sql += ' ORDER BY stt_nhom, ma_nvkd'
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        conn.close()

        seen_nv = {}
        kpi_sum = {}
        detail = {}
        flds = ['kpi', 'kpi_cong_ty', 'kpi_ds', 'kpi_ds_cong_ty']

        for r in rows:
            rd = {cols[i]: r[i] for i in range(len(cols))}
            ma = rd['ma_nvkd'] or ''
            if not ma:
                continue
            kbc = rd['ma_kbc'] or ''
            if ma not in seen_nv:
                seen_nv[ma] = {
                    'ma_nvkd': ma, 'ten_nvkd': rd['ten_nvkd'] or '',
                    'ma_ql': rd['ma_ql'] or '', 'ma_bp': rd['ma_bp'] or '',
                    'stt_nhom': rd['stt_nhom'] or '',
                }
            if ma not in kpi_sum:
                kpi_sum[ma] = {f: 0 for f in flds}
            for f in flds:
                kpi_sum[ma][f] += float(rd[f] or 0)
            if ma not in detail:
                detail[ma] = {}
            detail[ma][kbc] = {f: float(rd[f] or 0) for f in flds}

        return jsonify({'ok': True, 'assignments': list(seen_nv.values()), 'kpi': kpi_sum, 'detail': detail})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════
# API: Save single cell
# ═══════════════════════════════════════════════

@bp.route('/kpi/save-cell', methods=['POST'])
@admin_required
def kpi_save_cell():
    data = request.get_json(force=True)
    ma_kbc = data.get('ma_kbc', '').strip()
    ma_nvkd = data.get('ma_nvkd', '').strip()
    field = data.get('field', '')
    value = data.get('value', 0)

    if not ma_nvkd:
        return jsonify({'ok': False, 'error': 'Missing ma_nvkd'}), 400
    if field not in ('kpi', 'kpi_cong_ty', 'kpi_ds', 'kpi_ds_cong_ty'):
        return jsonify({'ok': False, 'error': 'Invalid field'}), 400

    try:
        conn = _ss_conn()
        cur = conn.cursor()
        # Check if row exists
        cur.execute('SELECT id FROM kpi_targets WHERE ma_kbc = ? AND ma_nvkd = ?', (ma_kbc, ma_nvkd))
        row = cur.fetchone()
        if row:
            cur.execute(f'UPDATE kpi_targets SET {field} = ?, ldate = GETDATE() WHERE ma_kbc = ? AND ma_nvkd = ?',
                        (value, ma_kbc, ma_nvkd))
        else:
            # Auto-create row if doesn't exist
            nam, thang = _parse_kbc(ma_kbc)
            cur.execute(
                f'INSERT INTO kpi_targets (ma_bp, ma_kbc, nam, thang, ma_nvkd, {field}) VALUES (?, ?, ?, ?, ?, ?)',
                ('', ma_kbc, nam, thang, ma_nvkd, value))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════
# API: Reassign (drag & drop)
# ═══════════════════════════════════════════════

@bp.route('/kpi/reassign', methods=['POST'])
@admin_required
def kpi_reassign():
    data = request.get_json(force=True)
    ma_kbc = data.get('ma_kbc', '').strip()
    ma_nvkd = data.get('ma_nvkd', '').strip()
    new_ma_ql = data.get('new_ma_ql', '').strip()

    if not ma_nvkd:
        return jsonify({'ok': False}), 400

    try:
        conn = _ss_conn()
        cur = conn.cursor()
        cur.execute('UPDATE kpi_targets SET ma_ql = ?, ldate = GETDATE() WHERE ma_kbc = ? AND ma_nvkd = ?',
                    (new_ma_ql, ma_kbc, ma_nvkd))
        conn.commit()
        # Recalc paths
        _recalc_paths(conn, ma_kbc)

        # Return updated assignments
        ma_bp = data.get('ma_bp', '')
        sql = 'SELECT ma_nvkd, ten_nvkd, ma_ql, ma_bp, stt_nhom FROM kpi_targets WHERE ma_kbc = ?'
        params = [ma_kbc]
        if ma_bp:
            sql += ' AND ma_bp = ?'
            params.append(ma_bp)
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        conn.close()

        assignments = []
        for r in rows:
            rd = {cols[i]: r[i] for i in range(len(cols))}
            assignments.append({
                'ma_nvkd': rd['ma_nvkd'] or '',
                'ten_nvkd': rd['ten_nvkd'] or '',
                'ma_ql': rd['ma_ql'] or '',
                'ma_bp': rd['ma_bp'] or '',
                'stt_nhom': rd['stt_nhom'] or '',
            })
        return jsonify({'ok': True, 'assignments': assignments})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════
# API: Copy period (clone kỳ trước → kỳ mới)
# ═══════════════════════════════════════════════

@bp.route('/kpi/copy-period', methods=['POST'])
@admin_required
def kpi_copy_period():
    data = request.get_json(force=True)
    from_kbc = data.get('from_kbc', '').strip()
    to_kbc = data.get('to_kbc', '').strip()
    ma_bp = data.get('ma_bp', '').strip()

    if not from_kbc or not to_kbc:
        return jsonify({'ok': False, 'error': 'Thiếu from_kbc hoặc to_kbc'}), 400

    nam, thang = _parse_kbc(to_kbc)

    try:
        conn = _ss_conn()
        cur = conn.cursor()

        # Check if target already has data
        cur.execute('SELECT COUNT(*) FROM kpi_targets WHERE ma_kbc = ?', (to_kbc,))
        cnt = cur.fetchone()[0]
        if cnt > 0:
            return jsonify({'ok': False, 'error': f'Kỳ {to_kbc} đã có {cnt} dòng. Xóa trước nếu muốn copy lại.'}), 400

        # Clone from source period
        sql = '''INSERT INTO kpi_targets
                    (ma_bp, ma_kbc, nam, thang, ma_nvkd, ten_nvkd, nguoi_gd,
                     ma_ql, stt_nhom, kpi, kpi_cong_ty, kpi_ds, kpi_ds_cong_ty, merge_kpi)
                 SELECT ma_bp, ?, ?, ?, ma_nvkd, ten_nvkd, nguoi_gd,
                        ma_ql, stt_nhom, kpi, kpi_cong_ty, kpi_ds, kpi_ds_cong_ty, merge_kpi
                 FROM kpi_targets WHERE ma_kbc = ?'''
        params = [to_kbc, nam, thang, from_kbc]
        if ma_bp:
            sql += ' AND ma_bp = ?'
            params.append(ma_bp)
        cur.execute(sql, params)
        copied = cur.rowcount
        conn.commit()
        conn.close()
        return jsonify({'ok': True, 'message': f'Đã copy {copied} dòng từ {from_kbc} → {to_kbc}'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════
# API: Import from DMNHANVIENKD_VIEW (hệ thống)
# ═══════════════════════════════════════════════

@bp.route('/kpi/import-system', methods=['POST'])
@admin_required
def kpi_import_system():
    data = request.get_json(force=True)
    ma_kbc = data.get('ma_kbc', '').strip()
    ma_bp = data.get('ma_bp', '').strip()

    if not ma_kbc:
        return jsonify({'ok': False, 'error': 'Thiếu ma_kbc'}), 400

    nam, thang = _parse_kbc(ma_kbc)

    try:
        conn = _ss_conn()
        cur = conn.cursor()

        # Get existing NVKDs for this period (to skip)
        cur.execute('SELECT ma_nvkd FROM kpi_targets WHERE ma_kbc = ?', (ma_kbc,))
        existing = set(r[0] for r in cur.fetchall())

        # Query current employees from system view
        sql_nv = "SELECT ma_nvkd, ten_nvkd, ma_ql FROM DMNHANVIENKD_VIEW WHERE ma_nvkd IS NOT NULL AND ma_nvkd != ''"
        cur.execute(sql_nv)
        nv_rows = cur.fetchall()

        # Determine BP for each NV from DMKHACHHANG_VIEW
        bp_map = {}
        if ma_bp:
            bp_map = {r[0]: ma_bp for r in nv_rows}  # all same BP
        else:
            cur.execute("""SELECT DISTINCT ma_nvkd, ma_bp FROM DMKHACHHANG_VIEW
                           WHERE ma_nvkd IS NOT NULL AND ma_nvkd != ''
                             AND ma_bp IS NOT NULL AND ma_bp != '' AND ma_bp != 'TN'""")
            for r in cur.fetchall():
                bp_map[r[0]] = r[1]

        inserted = 0
        skipped = 0
        for r in nv_rows:
            nv_ma = (r[0] or '').strip()
            if not nv_ma or nv_ma in existing:
                skipped += 1
                continue
            nv_ten = (r[1] or '').strip()
            nv_ql = (r[2] or '').strip()
            nv_bp = bp_map.get(nv_ma, ma_bp or '')

            if ma_bp and nv_bp != ma_bp:
                continue  # filter by BP

            cur.execute(
                '''INSERT INTO kpi_targets (ma_bp, ma_kbc, nam, thang, ma_nvkd, ten_nvkd, nguoi_gd, ma_ql)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (nv_bp, ma_kbc, nam, thang, nv_ma, nv_ten, nv_ten, nv_ql))
            inserted += 1

        conn.commit()
        # Recalc paths
        _recalc_paths(conn, ma_kbc)
        conn.close()
        return jsonify({'ok': True, 'message': f'Đã import {inserted} NV, bỏ qua {skipped} đã tồn tại'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════
# API: Export Excel
# ═══════════════════════════════════════════════

@bp.route('/kpi/export')
@admin_required
def kpi_export():
    from flask import send_file
    from io import BytesIO
    import openpyxl

    ma_kbc = request.args.get('ma_kbc', '').strip()
    ma_bp = request.args.get('ma_bp', '').strip()

    if not ma_kbc:
        return jsonify({'ok': False, 'error': 'Thiếu ma_kbc'}), 400

    try:
        conn = _ss_conn()
        cur = conn.cursor()
        sql = '''SELECT ma_bp, ma_kbc, nam, thang, ten_nvkd, nguoi_gd, ma_nvkd, ma_ql, stt_nhom,
                        kpi, merge_kpi, kpi_cong_ty, kpi_ds, kpi_ds_cong_ty, cdate
                 FROM kpi_targets WHERE ma_kbc = ?'''
        params = [ma_kbc]
        if ma_bp:
            sql += ' AND ma_bp = ?'
            params.append(ma_bp)
        sql += ' ORDER BY stt_nhom, ma_nvkd'
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        conn.close()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = ma_kbc
        ws.append(cols)
        for r in rows:
            ws.append(list(r))

        # Auto column width
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 30)

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        fname = f'KPI_{ma_kbc}_{ma_bp or "ALL"}.xlsx'
        return send_file(buf, download_name=fname, as_attachment=True,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════
# API: Import Excel
# ═══════════════════════════════════════════════

@bp.route('/kpi/import-excel', methods=['POST'])
@admin_required
def kpi_import_excel():
    """Import KPI từ file Excel.
    Cột bắt buộc: ma_nvkd, thang.
    ma_kbc tự build từ thang+nam nếu cột là formula.
    Mode: upsert (default) | skip.
    """
    import openpyxl
    from datetime import datetime as dt

    f = request.files.get('file')
    if not f:
        return jsonify({'ok': False, 'error': 'Không có file'}), 400

    mode = request.form.get('mode', 'upsert')

    try:
        wb = openpyxl.load_workbook(f, read_only=True, data_only=False)
        ws = wb[wb.sheetnames[0]]

        header = None
        for row in ws.iter_rows(max_row=1, values_only=True):
            header = [str(c or '').strip().lower() for c in row]
            break
        if not header:
            return jsonify({'ok': False, 'error': 'File rỗng'}), 400

        CI = {}
        for i, h in enumerate(header):
            CI[h] = i

        for req in ['ma_nvkd', 'thang']:
            if req not in CI:
                return jsonify({'ok': False, 'error': f'Thiếu cột: {req}'}), 400

        def g(row, col):
            idx = CI.get(col)
            if idx is None or idx >= len(row):
                return None
            return row[idx]

        def sf(v):
            if v is None: return 0
            try: return float(v)
            except: return 0

        def si(v):
            if v is None: return 0
            try: return int(v)
            except: return 0

        def ss(v):
            if v is None: return ''
            s = str(v).strip()
            return '' if s.startswith('=') else s

        records = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            ma_nvkd = ss(g(row, 'ma_nvkd'))
            if not ma_nvkd:
                continue
            thang = si(g(row, 'thang'))
            nam = si(g(row, 'nam')) or 2026
            ma_kbc_raw = ss(g(row, 'ma_kbc'))
            ma_kbc = ma_kbc_raw if ma_kbc_raw else f'T{thang:02d}-{nam}'

            records.append({
                'ma_bp': ss(g(row, 'ma_bp')),
                'ma_kbc': ma_kbc,
                'nam': nam, 'thang': thang,
                'ma_nvkd': ma_nvkd,
                'ten_nvkd': ss(g(row, 'ten_nvkd')),
                'nguoi_gd': ss(g(row, 'nguoi_gd')),
                'ma_ql': ss(g(row, 'ma_ql')),
                'stt_nhom': ss(g(row, 'stt_nhom')),
                'kpi': sf(g(row, 'kpi')),
                'kpi_cong_ty': sf(g(row, 'kpi_cong_ty')),
                'kpi_ds': sf(g(row, 'kpi_ds')),
                'kpi_ds_cong_ty': sf(g(row, 'kpi_ds_cong_ty')),
                'merge_kpi': si(g(row, 'merge_kpi')),
                'cdate': g(row, 'cdate'),
            })

        if not records:
            return jsonify({'ok': False, 'error': 'Không có dữ liệu hợp lệ'}), 400

        conn = _ss_conn()
        cur = conn.cursor()
        ins = upd = skp = 0

        for r in records:
            cur.execute('SELECT id FROM kpi_targets WHERE ma_kbc = ? AND ma_nvkd = ?',
                        (r['ma_kbc'], r['ma_nvkd']))
            exists = cur.fetchone()
            if exists:
                if mode == 'skip':
                    skp += 1
                    continue
                cur.execute('''UPDATE kpi_targets SET
                    ma_bp=?, nam=?, thang=?, ten_nvkd=?, nguoi_gd=?, ma_ql=?, stt_nhom=?,
                    kpi=?, kpi_cong_ty=?, kpi_ds=?, kpi_ds_cong_ty=?, merge_kpi=?, ldate=GETDATE()
                    WHERE ma_kbc=? AND ma_nvkd=?''',
                    (r['ma_bp'], r['nam'], r['thang'], r['ten_nvkd'], r['nguoi_gd'],
                     r['ma_ql'], r['stt_nhom'], r['kpi'], r['kpi_cong_ty'],
                     r['kpi_ds'], r['kpi_ds_cong_ty'], r['merge_kpi'],
                     r['ma_kbc'], r['ma_nvkd']))
                upd += 1
            else:
                cdate = r['cdate'] if isinstance(r['cdate'], dt) else None
                cur.execute('''INSERT INTO kpi_targets
                    (ma_bp, ma_kbc, nam, thang, ma_nvkd, ten_nvkd, nguoi_gd,
                     ma_ql, stt_nhom, kpi, kpi_cong_ty, kpi_ds, kpi_ds_cong_ty,
                     merge_kpi, cdate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (r['ma_bp'], r['ma_kbc'], r['nam'], r['thang'], r['ma_nvkd'],
                     r['ten_nvkd'], r['nguoi_gd'], r['ma_ql'], r['stt_nhom'],
                     r['kpi'], r['kpi_cong_ty'], r['kpi_ds'], r['kpi_ds_cong_ty'],
                     r['merge_kpi'], cdate))
                ins += 1

        conn.commit()
        conn.close()

        kbcs = sorted(set(r['ma_kbc'] for r in records))
        return jsonify({
            'ok': True,
            'message': f'{len(records)} dòng: +{ins} mới, ~{upd} cập nhật, ={skp} bỏ qua. Kỳ: {", ".join(kbcs)}'
        })

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500