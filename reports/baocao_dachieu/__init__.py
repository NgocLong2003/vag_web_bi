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


def _doanhthu_month(store, p, ma_bp, ds_nvkd, ds_kh, kh_bp, kh_names):
    """Doanh thu (thanh toán) 1 tháng — replicate logic gộp tt1+tt2 của baocao_kh."""
    bd_tt, kt_tt = p.get('bd_tt'), p.get('kt_tt')
    bd_xb, kt_xb = p.get('bd_xb'), p.get('kt_xb')
    bd_lk = p.get('bd_lk')
    if not bd_tt or not kt_tt:
        return {}
    # ngày trước lấn kỳ = bd_lk - 1
    ngay_truoc_lk = ''
    if bd_lk:
        try:
            ngay_truoc_lk = (datetime.strptime(bd_lk, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        except ValueError:
            ngay_truoc_lk = ''

    sql = load_sql('DOANHTHU_BCKH_DUCK')
    # tt1: nhóm A theo cửa sổ thu tiền [bd_tt..ngay_truoc_lk], nhóm B theo cửa sổ xuất bán [bd_xb..kt_xb]
    m1 = {}
    if bd_tt and ngay_truoc_lk:
        r1 = store.query(sql, [bd_tt, ngay_truoc_lk, bd_xb or None, kt_xb or None,
                               ma_bp or '', ds_nvkd or '', ds_kh or ''])
        m1 = _agg(r1, 'doanhthu', kh_names)
    # tt2: chỉ nhóm A (ngay_a2 = NULL ⇒ nhóm B bị loại trong query) [bd_lk..kt_tt]
    m2 = {}
    if bd_lk and kt_tt:
        r2 = store.query(sql, [bd_lk, kt_tt, None, None,
                               ma_bp or '', ds_nvkd or '', ds_kh or ''])
        m2 = _agg(r2, 'doanhthu', kh_names)

    merged = {}
    for nvkd, kh in m1.items():
        merged[nvkd] = dict(kh)
    for nvkd, kh in m2.items():
        dst = merged.setdefault(nvkd, {})
        for mk, v in kh.items():
            bp_kh = kh_bp.get(mk, '')
            if bp_kh and bp_kh not in BP_NHOM_A:
                continue  # nhóm B chỉ tính tt1
            dst[mk] = dst.get(mk, 0) + v
    return merged


# ─────────────────────────────────────────
# API: dữ liệu pivot — tính từng tháng cho từng measure
# ─────────────────────────────────────────
@bp.route('/api/data', methods=['POST'])
def api_data():
    body = request.get_json(force=True)
    periods = body.get('periods', [])           # list tháng-KBC với các trường ngày
    measures = body.get('measures', [])         # ['doanhso','soluong','doanhthu','tralai','thuong','congno']
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    if not periods:
        return api_response(ok=False, error='Thiếu danh sách kỳ', status_code=400)

    measures = set(measures) if measures else {'doanhso', 'soluong'}
    store = get_store()
    kh_names = {}

    # Map ma_kh → ma_bp (để lọc nhóm B cho doanh thu) — tái dùng KHACHHANG_DUCK
    kh_bp = {}
    try:
        for r in store.query(load_sql('KHACHHANG_DUCK')):
            if r.get('ma_kh'):
                kh_bp[r['ma_kh']] = r.get('ma_bp') or ''
    except Exception as e:
        logger.warning(f"[BCDC data] kh_bp load: {e}")

    out = {}
    for p in periods:
        pid = str(p.get('id'))
        bd_xb, kt_xb = p.get('bd_xb'), p.get('kt_xb')
        bd_tt, kt_tt = p.get('bd_tt'), p.get('kt_tt')
        bd_lk, kt_lk = p.get('bd_lk'), p.get('kt_lk')
        pres = {}

        try:
            # ── Doanh số / Số lượng (1 query DOANHSO_SQL_DUCK) ──
            if ('doanhso' in measures or 'soluong' in measures) and bd_xb and kt_xb:
                rows = store.query(load_sql('DOANHSO_SQL_DUCK'),
                                   [bd_xb, kt_xb, ma_bp or '', ds_nvkd or '', ds_kh or ''])
                if 'doanhso' in measures:
                    pres['doanhso'] = _agg(rows, 'tong_doanhso', kh_names)
                if 'soluong' in measures:
                    pres['soluong'] = _agg(rows, 'tong_so_luong', kh_names)

            # ── Trả lại ──
            if 'tralai' in measures and bd_xb and kt_xb:
                rows = store.query(load_sql('TRALAI_SQL_DUCK'),
                                   [bd_xb, kt_xb, ma_bp or '', ds_nvkd or '', ds_kh or ''])
                pres['tralai'] = _agg(rows, 'tong_tralai', kh_names)

            # ── Thưởng (cửa sổ thu tiền) ──
            if 'thuong' in measures and bd_tt and kt_tt:
                rows = store.query(load_sql('THUONG_SQL_DUCK'),
                                   [bd_tt, kt_tt, ma_bp or '', ds_nvkd or '', ds_kh or ''])
                pres['thuong'] = _agg(rows, 'tong_thuong', kh_names)

            # ── Doanh thu (thanh toán gộp) ──
            if 'doanhthu' in measures:
                pres['doanhthu'] = _doanhthu_month(store, p, ma_bp, ds_nvkd, ds_kh, kh_bp, kh_names)

            # ── Công nợ cuối kỳ (stock — chốt tại ngay_kt_thu_tien) ──
            if 'congno' in measures and kt_tt:
                try:
                    start_y = datetime.strptime(kt_tt, '%Y-%m-%d').year
                    has_lk = 1 if (bd_lk and kt_lk) else 0
                    rows = store.query(load_sql('DUNOCUOIKY_DUCK'),
                                       [kt_tt, start_y, bd_lk or None, kt_lk or None,
                                        has_lk, ma_bp or '', ds_nvkd or '', ds_kh or ''])
                    pres['congno'] = _agg(rows, 'du_no_cuoi_ky', kh_names)
                except ValueError:
                    pass
        except Exception as e:
            logger.error(f"[BCDC data] period {pid}: {e}")

        out[pid] = pres

    return api_response(ok=True, data=out, count=len(periods),
                        kh_names=kh_names,
                        meta={'measures': sorted(measures)})


# ─────────────────────────────────────────
# API: Dữ liệu chi tiết dòng-hàng (chiều Sản phẩm / Khu vực)
# Trả về rows aggregated theo từng tháng → frontend tự pivot mọi chiều.
# ─────────────────────────────────────────
@bp.route('/api/data_detail', methods=['POST'])
def api_data_detail():
    body = request.get_json(force=True)
    periods = body.get('periods', [])
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    if not periods:
        return api_response(ok=False, error='Thiếu danh sách kỳ', status_code=400)

    store = get_store()
    sql = load_sql('DACHIEU_FACT_DUCK')
    out = {}
    for p in periods:
        pid = str(p.get('id'))
        bd_xb, kt_xb = p.get('bd_xb'), p.get('kt_xb')
        rows = []
        if bd_xb and kt_xb:
            try:
                rows = store.query(sql, [bd_xb, kt_xb, ma_bp or '', ds_nvkd or '', ds_kh or ''])
                for d in rows:
                    for k in ('so_luong', 'doanhso'):
                        if d.get(k) is not None:
                            d[k] = float(d[k])
            except Exception as e:
                logger.error(f"[BCDC data_detail] period {pid}: {e}")
        out[pid] = rows

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
