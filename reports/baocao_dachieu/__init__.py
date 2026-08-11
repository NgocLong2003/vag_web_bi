"""
Báo cáo Đa Chiều — Blueprint (DuckDB version)
API prefix: /reports/bao-cao-da-chieu/api/...

Pivot đa chiều: NVKD tree (hàng) × Kỳ tháng/quý/năm (cột) × các measure
(doanh số, số lượng, doanh thu, trả lại, thưởng, công nợ cuối kỳ).

NGUYÊN TẮC TÁI DÙNG (không tạo logic mới, không đụng báo cáo khác):
  - Tái dùng NGUYÊN các query đã có: DOANHSO_SQL_DUCK, TRALAI_SQL_DUCK,
    THUONG_SQL_DUCK, DOANHTHU_BCKH_DUCK, DUNOCUOIKY_DUCK
    (cùng các query nền KY_BAO_CAO/HIERARCHY/KHACHHANG).
  - Mỗi measure được tính ở grain THÁNG (1 kỳ báo cáo loại 'Tháng').
    Frontend gom tháng → quý/năm: flow thì CỘNG, công nợ (stock) lấy THÁNG CUỐI.
  - Doanh thu replicate ĐÚNG logic gộp tt1+tt2 (lọc nhóm B) của baocao_khachhang
    để con số khớp tuyệt đối với báo cáo Khách Hàng.
"""
from flask import Blueprint, request, current_app
from api_logger import api_response
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('bcdc', __name__,
               url_prefix='/reports/bao-cao-da-chieu',
               template_folder='templates')
bp.api_report = 'bao-cao-da-chieu'
from query_loader import load_sql


def get_store():
    return current_app.config['DUCKDB_STORE']


BP_NHOM_A = {'VA', 'VB', 'SF'}


# ─────────────────────────────────────────
# API nền (giống các báo cáo khác)
# ─────────────────────────────────────────
@bp.route('/api/ky-bao-cao')
def api_ky_bao_cao():
    try:
        data = get_store().query(load_sql('KY_BAO_CAO_DUCK'))
        return api_response(ok=True, data=data, count=len(data))
    except Exception as e:
        logger.error(f"[BCDC ky_bao_cao] {e}")
        return api_response(ok=False, error=str(e))


@bp.route('/api/hierarchy')
def api_hierarchy():
    try:
        data = get_store().query(load_sql('HIERARCHY_CTE_DUCK'))
        return api_response(ok=True, data=data, count=len(data))
    except Exception as e:
        logger.error(f"[BCDC hierarchy] {e}")
        return api_response(ok=False, error=str(e))


@bp.route('/api/khachhang')
def api_khachhang():
    try:
        data = get_store().query(load_sql('KHACHHANG_DUCK'))
        return api_response(ok=True, data=data, count=len(data))
    except Exception as e:
        logger.error(f"[BCDC khachhang] {e}")
        return api_response(ok=False, error=str(e))


# ─────────────────────────────────────────
# Helpers — gom kết quả query về {ma_nvkd: {ma_kh: value}}
# ─────────────────────────────────────────
def _agg(rows, val_key, kh_names):
    """Gom rows → {ma_nvkd: {ma_kh: sum(value)}}. Đồng thời thu thập tên KH."""
    out = {}
    for r in rows:
        nvkd = r.get('ma_nvkd') or '_UNK'
        mk = r.get('ma_kh')
        if mk is None:
            continue
        v = r.get(val_key)
        if v is None:
            continue
        bucket = out.setdefault(nvkd, {})
        bucket[mk] = bucket.get(mk, 0) + float(v)
        tk = r.get('ten_kh')
        if tk:
            kh_names[mk] = tk
    return out


import re as _re
import gzip as _gzip
_DATE_RE = _re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _dlit(v):
    """DATE literal an toàn (validate ISO) hoặc NULL — chống injection khi inline."""
    return "DATE '%s'" % v if (v and _DATE_RE.match(v)) else "NULL"


def _pvals(periods, keys):
    """Dựng các dòng VALUES: (pid, <date literals theo keys>)."""
    rows = []
    for p in periods:
        cells = [str(int(p.get('id')))] + [_dlit(p.get(k)) for k in keys]
        rows.append('(' + ','.join(cells) + ')')
    return ',\n'.join(rows)


def _fold(out, measure, rows, nv_key, kh_key, val_key, kh_names=None, name_key=None):
    """Gộp rows (có cột pid) vào out[pid][measure][nvkd][kh] += val."""
    for r in rows:
        pid = str(r.get('pid'))
        if pid not in out:
            continue
        mk = r.get(kh_key)
        if mk is None:
            continue
        v = r.get(val_key)
        if v is None:
            continue
        nv = r.get(nv_key) or '_UNK'
        d = out[pid].setdefault(measure, {}).setdefault(nv, {})
        d[mk] = d.get(mk, 0) + float(v)
        if kh_names is not None and name_key and r.get(name_key):
            kh_names[mk] = r[name_key]


# Chuẩn hoá NVKD (NVQ02@VB → NVQ03) — {a} = alias bảng
_NVNORM = "CASE WHEN {a}.ma_nvkd='NVQ02' AND {a}.ma_bp='VB' THEN 'NVQ03' ELSE {a}.ma_nvkd END"


@bp.after_request
def _bcdc_gzip(resp):
    """Nén gzip cho JSON lớn (payload chi tiết có thể vài chục MB)."""
    try:
        ae = request.headers.get('Accept-Encoding', '')
        ct = resp.content_type or ''
        if 'gzip' in ae and ct.startswith('application/json') and 'Content-Encoding' not in resp.headers:
            data = resp.get_data()
            if len(data) > 2048:
                resp.set_data(_gzip.compress(data, 5))
                resp.headers['Content-Encoding'] = 'gzip'
                resp.headers['Vary'] = 'Accept-Encoding'
    except Exception as e:
        logger.warning(f"[BCDC gzip] {e}")
    return resp


# ─────────────────────────────────────────
# API: dữ liệu pivot — 1 LẦN QUÉT/measure rồi bucket theo kỳ (nhanh hơn ~10×)
# ─────────────────────────────────────────
@bp.route('/api/data', methods=['POST'])
def api_data():
    body = request.get_json(force=True)
    periods = body.get('periods', [])
    measures = body.get('measures', [])
    ma_bp = body.get('ma_bp', '') or ''
    ds_nvkd = body.get('ds_nvkd', '') or ''
    ds_kh = body.get('ds_kh', '') or ''

    if not periods:
        return api_response(ok=False, error='Thiếu danh sách kỳ', status_code=400)

    measures = set(measures) if measures else {'doanhso', 'soluong'}
    store = get_store()
    kh_names = {}
    flt = [ma_bp, ds_nvkd, ds_kh]
    out = {str(p.get('id')): {} for p in periods}

    try:
        # ── Doanh số / Số lượng — 1 lần quét BKHDBANHANG, bucket [bd_xb,kt_xb] ──
        if 'doanhso' in measures or 'soluong' in measures:
            pv = _pvals(periods, ['bd_xb', 'kt_xb']); nvn = _NVNORM.format(a='b')
            sql = f'''
WITH periods(pid,a,b) AS (VALUES {pv})
SELECT p.pid AS pid, {nvn} AS ma_nvkd, b.ma_kh,
       SUM(b.so_luong) AS sl, SUM(b.tien_nt2-b.tien_ck_nt) AS ds
FROM BKHDBANHANG b JOIN periods p ON b.ngay_ct>=p.a AND b.ngay_ct<=p.b
WHERE ($1='' OR b.ma_bp IN (SELECT TRIM(unnest(string_split($1,',')))))
  AND ($2='' OR {nvn} IN (SELECT TRIM(unnest(string_split($2,',')))))
  AND ($3='' OR b.ma_kh IN (SELECT TRIM(unnest(string_split($3,',')))))
GROUP BY p.pid, 2, b.ma_kh'''
            rows = store.query(sql, flt)
            if 'doanhso' in measures:
                _fold(out, 'doanhso', rows, 'ma_nvkd', 'ma_kh', 'ds')
            if 'soluong' in measures:
                _fold(out, 'soluong', rows, 'ma_nvkd', 'ma_kh', 'sl')

        # ── Trả lại — TRALAI, [bd_xb,kt_xb] ──
        if 'tralai' in measures:
            pv = _pvals(periods, ['bd_xb', 'kt_xb']); nvn = _NVNORM.format(a='t')
            sql = f'''
WITH periods(pid,a,b) AS (VALUES {pv})
SELECT p.pid AS pid, {nvn} AS ma_nvkd, t.ma_kh, SUM(t.tien_nt2-t.tien_ck_nt) AS tl
FROM TRALAI t JOIN periods p ON t.ngay_ct>=p.a AND t.ngay_ct<=p.b
WHERE ($1='' OR t.ma_bp IN (SELECT TRIM(unnest(string_split($1,',')))))
  AND ($2='' OR {nvn} IN (SELECT TRIM(unnest(string_split($2,',')))))
  AND ($3='' OR t.ma_kh IN (SELECT TRIM(unnest(string_split($3,',')))))
GROUP BY p.pid, 2, t.ma_kh'''
            _fold(out, 'tralai', store.query(sql, flt), 'ma_nvkd', 'ma_kh', 'tl')

        # ── Thưởng — THUONG, [bd_tt,kt_tt] ──
        if 'thuong' in measures:
            pv = _pvals(periods, ['bd_tt', 'kt_tt'])
            sql = f'''
WITH periods(pid,a,b) AS (VALUES {pv})
SELECT p.pid AS pid, t.ma_nvkd, t.ma_kh_ct AS ma_kh, SUM(t.thuong) AS th
FROM THUONG t JOIN periods p ON t.ngay_ct>=p.a AND t.ngay_ct<=p.b
WHERE ($1='' OR t.ma_bp IN (SELECT TRIM(unnest(string_split($1,',')))))
  AND ($2='' OR t.ma_nvkd IN (SELECT TRIM(unnest(string_split($2,',')))))
  AND ($3='' OR t.ma_kh_ct IN (SELECT TRIM(unnest(string_split($3,',')))))
GROUP BY p.pid, t.ma_nvkd, t.ma_kh_ct'''
            _fold(out, 'thuong', store.query(sql, flt), 'ma_nvkd', 'ma_kh', 'th')

        # ── Doanh thu — PTHUBAOCO. Nhóm A: [bd_tt,kt_tt] · Nhóm B: [bd_xb,kt_xb]
        #    (tt1∪tt2 nhóm A = [bd_tt,kt_tt] vì truoc_lk = bd_lk-1) — khớp logic gộp cũ
        if 'doanhthu' in measures:
            pv = _pvals(periods, ['bd_tt', 'kt_tt', 'bd_xb', 'kt_xb'])
            sql = f'''
WITH periods(pid,bd_tt,kt_tt,bd_xb,kt_xb) AS (VALUES {pv})
SELECT p.pid AS pid, t.ma_nvkd, t.ma_kh_ct AS ma_kh, SUM(t.ps_co) AS dt
FROM PTHUBAOCO t JOIN periods p ON (
   (t.ma_bp IN ('VA','VB','SF') AND t.ngay_ct>=p.bd_tt AND t.ngay_ct<=p.kt_tt)
   OR (t.ma_bp NOT IN ('VA','VB','SF') AND t.ngay_ct>=p.bd_xb AND t.ngay_ct<=p.kt_xb))
WHERE t.tk_co='131'
  AND ((t.ngay_ct>=DATE '2026-01-01' AND t.tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
       OR (t.ngay_ct<DATE '2026-01-01' AND t.ma_ct='CA1'))
  AND ($1='' OR t.ma_bp IN (SELECT TRIM(unnest(string_split($1,',')))))
  AND ($2='' OR t.ma_nvkd IN (SELECT TRIM(unnest(string_split($2,',')))))
  AND ($3='' OR t.ma_kh_ct IN (SELECT TRIM(unnest(string_split($3,',')))))
GROUP BY p.pid, t.ma_nvkd, t.ma_kh_ct'''
            _fold(out, 'doanhthu', store.query(sql, flt), 'ma_nvkd', 'ma_kh', 'dt')

        # ── Công nợ cuối kỳ (stock, cumulative) — vẫn tính từng tháng ──
        if 'congno' in measures:
            cnq = load_sql('DUNOCUOIKY_DUCK')
            for p in periods:
                kt_tt, bd_lk, kt_lk = p.get('kt_tt'), p.get('bd_lk'), p.get('kt_lk')
                if not kt_tt:
                    continue
                try:
                    start_y = datetime.strptime(kt_tt, '%Y-%m-%d').year
                except ValueError:
                    continue
                has_lk = 1 if (bd_lk and kt_lk) else 0
                rows = store.query(cnq, [kt_tt, start_y, bd_lk or None, kt_lk or None,
                                         has_lk, ma_bp, ds_nvkd, ds_kh])
                _fold(out, 'congno', [dict(r, pid=p.get('id')) for r in rows],
                      'ma_nvkd', 'ma_kh', 'du_no_cuoi_ky', kh_names, 'ten_kh')
    except Exception as e:
        logger.error(f"[BCDC data] {e}")
        return api_response(ok=False, error=str(e))

    return api_response(ok=True, data=out, count=len(periods),
                        kh_names=kh_names, meta={'measures': sorted(measures)})


# ─────────────────────────────────────────
# API: Dữ liệu chi tiết dòng-hàng — 1 LẦN QUÉT (bucket theo kỳ)
# ─────────────────────────────────────────
@bp.route('/api/data_detail', methods=['POST'])
def api_data_detail():
    body = request.get_json(force=True)
    periods = body.get('periods', [])
    ma_bp = body.get('ma_bp', '') or ''
    ds_nvkd = body.get('ds_nvkd', '') or ''
    ds_kh = body.get('ds_kh', '') or ''

    if not periods:
        return api_response(ok=False, error='Thiếu danh sách kỳ', status_code=400)

    store = get_store()
    pv = _pvals(periods, ['bd_xb', 'kt_xb'])
    sql = f'''
WITH periods(pid,a,b) AS (VALUES {pv}),
combined AS (
    SELECT p.pid AS pid,
        CASE WHEN b.ma_nvkd='NVQ02' AND b.ma_bp='VB' THEN 'NVQ03' ELSE b.ma_nvkd END AS ma_nvkd,
        b.ma_kh, b.ma_vt, b.ten_vt, b.ma_bp,
        b.so_luong AS so_luong, b.tien_nt2-b.tien_ck_nt AS doanhso, 0 AS tralai
    FROM BKHDBANHANG b JOIN periods p ON b.ngay_ct>=p.a AND b.ngay_ct<=p.b
    UNION ALL
    SELECT p.pid AS pid,
        CASE WHEN t.ma_nvkd='NVQ02' AND t.ma_bp='VB' THEN 'NVQ03' ELSE t.ma_nvkd END AS ma_nvkd,
        t.ma_kh, t.ma_vt, t.ten_vt, t.ma_bp,
        0 AS so_luong, 0 AS doanhso, t.tien_nt2-t.tien_ck_nt AS tralai
    FROM TRALAI t JOIN periods p ON t.ngay_ct>=p.a AND t.ngay_ct<=p.b
)
SELECT c.pid AS pid, c.ma_nvkd, c.ma_kh,
    COALESCE(NULLIF(kh.ten_kh,''), c.ma_kh) AS ten_kh,
    COALESCE(NULLIF(kh.ten_plkh1,''), '(Không khu vực)') AS ten_plkh1,
    c.ma_vt, COALESCE(NULLIF(c.ten_vt,''), c.ma_vt) AS ten_vt,
    COALESCE(NULLIF(d.ten_thuoc,''), '(Không dòng SP)') AS ten_thuoc,
    SUM(c.so_luong) AS so_luong, SUM(c.doanhso) AS doanhso, SUM(c.tralai) AS tralai
FROM combined c
LEFT JOIN DMKHACHHANG kh ON kh.ma_kh=c.ma_kh
LEFT JOIN DMSANPHAM d ON d.ma_vt=c.ma_vt
WHERE ($1='' OR c.ma_bp IN (SELECT TRIM(unnest(string_split($1,',')))))
  AND ($2='' OR c.ma_nvkd IN (SELECT TRIM(unnest(string_split($2,',')))))
  AND ($3='' OR c.ma_kh IN (SELECT TRIM(unnest(string_split($3,',')))))
GROUP BY c.pid, c.ma_nvkd, c.ma_kh, COALESCE(NULLIF(kh.ten_kh,''),c.ma_kh),
    COALESCE(NULLIF(kh.ten_plkh1,''),'(Không khu vực)'), c.ma_vt,
    COALESCE(NULLIF(c.ten_vt,''),c.ma_vt), COALESCE(NULLIF(d.ten_thuoc,''),'(Không dòng SP)')'''

    out = {str(p.get('id')): [] for p in periods}
    try:
        for r in store.query(sql, [ma_bp, ds_nvkd, ds_kh]):
            pid = str(r.pop('pid'))
            for k in ('so_luong', 'doanhso', 'tralai'):
                if r.get(k) is not None:
                    r[k] = float(r[k])
            if pid in out:
                out[pid].append(r)
    except Exception as e:
        logger.error(f"[BCDC data_detail] {e}")
        return api_response(ok=False, error=str(e))

    return api_response(ok=True, data=out, count=len(periods))


# ─────────────────────────────────────────
# API: Export Excel (clone mẫu baocao_khachhang — NV tree + KH + tổng)
# ─────────────────────────────────────────
@bp.route('/api/export_excel', methods=['POST'])
def api_export_excel():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from io import BytesIO

    body = request.get_json(force=True)
    rows = body.get('rows', [])
    col_headers = body.get('col_headers', [])
    kbc_name = body.get('kbc_name', '')

    if not rows:
        return api_response(ok=False, error='Không có dữ liệu', status_code=400)

    max_nv_depth = max((r.get('depth', 0) for r in rows if r.get('type') == 'nv'), default=0)
    nv_cols = max_nv_depth + 1
    name_col = nv_cols + 1
    data_start = nv_cols + 2

    wb = Workbook()
    ws = wb.active
    ws.title = 'Báo cáo đa chiều'
    FN = 'Arial'
    BK = '000000'
    thin = Border(bottom=Side(style='thin', color='D5D9E4'), right=Side(style='thin', color='ECEEF3'))
    hdr = Border(bottom=Side(style='medium', color='A0AAC0'))
    tot = Border(top=Side(style='medium', color='8090B0'), bottom=Side(style='medium', color='8090B0'))
    bgs = ['B8C6F0', 'CADAF6', 'DAEAFC', 'E8F0FD', 'F0F5FE', 'F7FAFE']

    def nbg(d): return bgs[min(d, len(bgs) - 1)]
    def nsz(d): return 11 if d == 0 else 10.5 if d == 1 else 10

    for c in range(1, nv_cols + 1):
        cell = ws.cell(row=1, column=c, value='NHÂN VIÊN KINH DOANH' if c == 1 else '')
        cell.font = Font(name=FN, bold=True, size=11, color=BK)
        cell.fill = PatternFill('solid', fgColor='D0D8ED')
        cell.alignment = Alignment(vertical='center')
        cell.border = hdr
    kh = ws.cell(row=1, column=name_col, value='KHÁCH HÀNG')
    kh.font = Font(name=FN, bold=True, size=11, color=BK)
    kh.fill = PatternFill('solid', fgColor='D0D8ED')
    kh.alignment = Alignment(vertical='center')
    kh.border = hdr
    for ci, ch in enumerate(col_headers):
        cell = ws.cell(row=1, column=data_start + ci, value=ch)
        cell.font = Font(name=FN, bold=True, size=10.5, color=BK)
        cell.fill = PatternFill('solid', fgColor='D0D8ED')
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        cell.border = hdr
    ws.row_dimensions[1].height = 40

    cur_row = 1
    for rd in rows:
        cur_row += 1
        rt = rd.get('type', '')
        dp = rd.get('depth', 0)
        nm = rd.get('name', '')
        vs = rd.get('values', [])
        tc = data_start + len(col_headers) - 1

        if rt == 'nv':
            ws.cell(row=cur_row, column=min(dp, nv_cols - 1) + 1, value=nm)
            bg = nbg(dp)
            sz = nsz(dp)
            for c in range(1, tc + 1):
                cell = ws.cell(row=cur_row, column=c)
                cell.fill = PatternFill('solid', fgColor=bg)
                cell.border = thin
                cell.font = Font(name=FN, bold=True, size=sz, color=BK)
                cell.alignment = Alignment(vertical='center', horizontal='right' if c >= data_start else 'left')
                if c >= data_start:
                    cell.number_format = '#,##0'
            for vi, v in enumerate(vs):
                if v is not None and v != '':
                    ws.cell(row=cur_row, column=data_start + vi, value=v)

        elif rt == 'kh':
            ws.cell(row=cur_row, column=name_col, value=nm)
            for c in range(1, tc + 1):
                cell = ws.cell(row=cur_row, column=c)
                cell.fill = PatternFill('solid', fgColor='FFFFFF')
                cell.border = thin
                cell.font = Font(name=FN, size=10, color=BK)
                cell.alignment = Alignment(vertical='center', horizontal='right' if c >= data_start else 'left')
                if c >= data_start:
                    cell.number_format = '#,##0'
            for vi, v in enumerate(vs):
                if v is not None and v != '':
                    ws.cell(row=cur_row, column=data_start + vi, value=v)

        elif rt == 'total':
            ws.cell(row=cur_row, column=1, value='TỔNG CỘNG')
            for c in range(1, tc + 1):
                cell = ws.cell(row=cur_row, column=c)
                cell.fill = PatternFill('solid', fgColor='B8C6F0')
                cell.border = tot
                cell.font = Font(name=FN, bold=True, size=11, color=BK)
                cell.alignment = Alignment(vertical='center', horizontal='right' if c >= data_start else 'left')
                if c >= data_start:
                    cell.number_format = '#,##0'
            for vi, v in enumerate(vs):
                if v is not None and v != '':
                    ws.cell(row=cur_row, column=data_start + vi, value=v)

        ws.row_dimensions[cur_row].height = 19

    for c in range(1, nv_cols + 1):
        ws.column_dimensions[get_column_letter(c)].width = 6
    ws.column_dimensions[get_column_letter(name_col)].width = 32
    for ci in range(len(col_headers)):
        ws.column_dimensions[get_column_letter(data_start + ci)].width = 18
    ws.freeze_panes = ws.cell(row=2, column=data_start)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    from flask import send_file
    now = datetime.now()
    filename = f'BaoCaoDaChieu_{now.strftime("%Y%m%d")}.xlsx'

    from api_logger import set_api_result
    set_api_result(status='ok', row_count=len(rows), meta={'export': filename, 'kbc_name': kbc_name})

    return send_file(buf,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)
