"""
Báo cáo Chi Tiết Bán Hàng & Thanh Toán — Blueprint
APIs: hierarchy, khachhang, doanhso_chitiet, doanhthu_chitiet, export_excel
Prefix: /reports/bao-cao-chi-tiet/api/...
"""
from flask import Blueprint, jsonify, request, send_file
from datetime import datetime, date
import pyodbc
import logging
from config import SQLSERVER_CONFIG

logger = logging.getLogger(__name__)

bp = Blueprint('bcct', __name__,
               url_prefix='/reports/bao-cao-chi-tiet',
               template_folder='templates')


def get_connection():
    c = SQLSERVER_CONFIG
    return pyodbc.connect(
        f"DRIVER={{{c['driver']}}};SERVER={c['server']},{c['port']};"
        f"DATABASE={c['database']};UID={c['username']};PWD={c['password']};"
        "TrustServerCertificate=yes;Connect Timeout=30;")


def rows_to_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def serialize_row(d):
    for k, v in d.items():
        if isinstance(v, (datetime, date)):
            d[k] = v.isoformat()
        elif v is not None and not isinstance(v, (str, int, float, bool)):
            d[k] = str(v)
    return d


HIERARCHY_CTE = """
    NV_BASE AS (
        SELECT ma_nvkd,
               CASE
               WHEN ma_nvkd = 'DTD01' THEN 'TVV01'
               WHEN ma_nvkd = 'PQT01' THEN 'TVV01'
               WHEN ma_nvkd = 'BCT02' THEN 'TVV01'
               WHEN ma_nvkd = 'NTT02' THEN 'TVV01'
               ELSE ma_ql END AS ma_ql,
               ten_nvkd
        FROM DMNHANVIENKD_VIEW
        UNION ALL SELECT 'VB99','VB00',N'Khác'
        UNION ALL SELECT 'VA99','TVV01',N'Khác'
        UNION ALL SELECT 'SF99','PVT04',N'Khác'
        UNION ALL SELECT 'DF99','NVD01',N'Khác'
        UNION ALL SELECT 'XK99','XK00',N'Khác'
        UNION ALL SELECT 'DA99','DA00',N'Khác'
    ),
    RecursiveHierarchy AS (
        SELECT v.ma_nvkd, v.ma_ql, v.ten_nvkd,
            CAST(v.ma_nvkd AS NVARCHAR(MAX)) AS stt_nhom, 0 AS level
        FROM NV_BASE v
        LEFT JOIN NV_BASE parent ON v.ma_ql = parent.ma_nvkd
        WHERE v.ma_ql IS NULL OR v.ma_ql = '' OR parent.ma_nvkd IS NULL
        UNION ALL
        SELECT e.ma_nvkd, e.ma_ql, e.ten_nvkd,
            CAST(rh.stt_nhom + '.' + e.ma_nvkd AS NVARCHAR(MAX)), rh.level + 1
        FROM NV_BASE e
        INNER JOIN RecursiveHierarchy rh ON e.ma_ql = rh.ma_nvkd
    )
"""


@bp.route('/api/hierarchy')
def api_hierarchy():
    sql = ";WITH " + HIERARCHY_CTE + """
    SELECT ma_nvkd, ten_nvkd, ma_ql, stt_nhom, level
    FROM RecursiveHierarchy ORDER BY stt_nhom;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql)
        data = rows_to_dict(cur)
        conn.close()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[BCCT hierarchy] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/khachhang')
def api_khachhang():
    sql = """SELECT DISTINCT ma_kh, ten_kh, ma_bp, ma_nvkd
    FROM DMKHACHHANG_VIEW WHERE ma_bp IS NOT NULL AND ma_bp != 'TN' AND ma_kh != 'TTT'"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql)
        data = rows_to_dict(cur)
        conn.close()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[BCCT khachhang] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────
# API: Doanh số chi tiết
# ─────────────────────────────────────────
@bp.route('/api/doanhso_chitiet', methods=['POST'])
def api_doanhso_chitiet():
    body = request.get_json(force=True)
    ngay_a = body.get('ngay_a', '')
    ngay_b = body.get('ngay_b', '')
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    if not ngay_a or not ngay_b:
        return jsonify({'success': False, 'error': 'Thiếu ngày'}), 400

    logger.info(f"[BCCT doanhso] {ngay_a}→{ngay_b}, bp='{ma_bp}', nv='{ds_nvkd}'")

    sql = """
    DECLARE @NgayA DATE=?; DECLARE @NgayB DATE=?;
    DECLARE @MaBP NVARCHAR(MAX)=?; DECLARE @DSMaNVKD NVARCHAR(MAX)=?; DECLARE @DSMaKH NVARCHAR(MAX)=?;
    SELECT
        ngay_ct,
        CASE WHEN ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,ngay_ct) ELSE ngay_ct END AS ngay_admin,
        CASE WHEN ma_nvkd='NVQ02' AND ma_bp='VB' THEN 'NVQ03' ELSE ma_nvkd END AS ma_nvkd,
        ma_kh, ma_vt, ten_vt, dvt,
        so_luong, gia_nt2, tien_nt2, tien_ck_nt, ts_gtgt, thue_gtgt_nt,
        tien_nt2-tien_ck_nt AS doanhso, ma_bp
    FROM [dbo].[BKHDBANHANG_VIEW]
    WHERE ma_bp!='TN'
      AND CASE WHEN ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,ngay_ct) ELSE ngay_ct END>=@NgayA
      AND CASE WHEN ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,ngay_ct) ELSE ngay_ct END<=@NgayB
      AND (@MaBP='' OR @MaBP IS NULL OR ma_bp IN (SELECT TRIM(value) FROM STRING_SPLIT(@MaBP,',')))
      AND (@DSMaNVKD='' OR CASE WHEN ma_nvkd='NVQ02' AND ma_bp='VB' THEN 'NVQ03' ELSE ma_nvkd END
           IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD,',')))
      AND (@DSMaKH='' OR ma_kh IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH,',')))
    ORDER BY CASE WHEN ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,ngay_ct) ELSE ngay_ct END, ma_kh, ma_nvkd;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (ngay_a, ngay_b, ma_bp or '', ds_nvkd or '', ds_kh or ''))
        data = []
        for row in cur.fetchall():
            cols = [c[0] for c in cur.description]
            d = dict(zip(cols, row))
            for fld in ('so_luong', 'gia_nt2', 'tien_nt2', 'tien_ck_nt', 'ts_gtgt', 'thue_gtgt_nt', 'doanhso'):
                if d.get(fld) is not None: d[fld] = float(d[fld])
            d = serialize_row(d)
            data.append(d)
        conn.close()
        logger.info(f"[BCCT doanhso] Returned {len(data)} rows")
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[BCCT doanhso] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────
# API: Doanh thu chi tiết
# ─────────────────────────────────────────
@bp.route('/api/doanhthu_chitiet', methods=['POST'])
def api_doanhthu_chitiet():
    body = request.get_json(force=True)
    ngay_a = body.get('ngay_a', '')
    ngay_b = body.get('ngay_b', '')
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    if not ngay_a or not ngay_b:
        return jsonify({'success': False, 'error': 'Thiếu ngày'}), 400

    logger.info(f"[BCCT doanhthu] {ngay_a}→{ngay_b}, bp='{ma_bp}', nv='{ds_nvkd}'")

    sql = """
    DECLARE @NgayA DATE=?; DECLARE @NgayB DATE=?;
    DECLARE @MaBP NVARCHAR(MAX)=?; DECLARE @DSMaNVKD NVARCHAR(MAX)=?; DECLARE @DSMaKH NVARCHAR(MAX)=?;

    SELECT dt.ngay_ct,dt.ma_kh_ct,dt.ma_bp,dt.ps_co,dt.ten_kh,dt.dien_giai
    INTO #TempDoanhThu_CT FROM PTHUBAOCO_VIEW dt
    WHERE dt.tk_co='131' AND dt.ma_bp!='TN'
      AND ((dt.ngay_ct>='2026-01-01' AND dt.tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
        OR (dt.ngay_ct<'2026-01-01' AND dt.ma_ct='CA1'))
      AND (@MaBP IS NULL OR @MaBP='' OR dt.ma_bp IN (SELECT TRIM(value) FROM STRING_SPLIT(@MaBP,',')))
      AND dt.ngay_ct>=@NgayA AND dt.ngay_ct<=@NgayB
      AND (@DSMaKH='' OR dt.ma_kh_ct IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH,',')));

    CREATE INDEX IX_Temp_CT_KH ON #TempDoanhThu_CT(ma_kh_ct,ngay_ct);
    SELECT DISTINCT ma_kh_ct INTO #MaKH_CT FROM #TempDoanhThu_CT;

    SELECT ds.ma_kh,ds.ma_nvkd,ds.ngay_ct INTO #TempDS_CT
    FROM BKHDBANHANG_VIEW ds INNER JOIN #MaKH_CT mk ON ds.ma_kh=mk.ma_kh_ct;
    CREATE INDEX IX_TDS_CT ON #TempDS_CT(ma_kh,ngay_ct DESC);

    SELECT dmkh.ma_kh,dmkh.ma_nvkd INTO #TempDMKH_CT
    FROM DMKHACHHANG_VIEW dmkh INNER JOIN #MaKH_CT mk ON dmkh.ma_kh=mk.ma_kh_ct;
    CREATE INDEX IX_TDMKH_CT ON #TempDMKH_CT(ma_kh);

    SELECT dt.ngay_ct,
        CASE WHEN dt.ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,dt.ngay_ct) ELSE dt.ngay_ct END AS ngay_admin,
        dt.ma_kh_ct AS ma_kh, dt.ten_kh, dt.dien_giai, dt.ma_bp,
        COALESCE(ds.ma_nvkd,dmkh.ma_nvkd) AS ma_nvkd,
        dt.ps_co AS doanhthu
    INTO #KQ_CT
    FROM #TempDoanhThu_CT dt
    OUTER APPLY (SELECT TOP 1 ma_nvkd FROM #TempDS_CT tds WHERE tds.ma_kh=dt.ma_kh_ct AND tds.ngay_ct<=dt.ngay_ct ORDER BY tds.ngay_ct DESC) ds
    OUTER APPLY (SELECT TOP 1 ma_nvkd FROM #TempDMKH_CT tdmkh WHERE tdmkh.ma_kh=dt.ma_kh_ct) dmkh
    WHERE @DSMaNVKD='' OR COALESCE(ds.ma_nvkd,dmkh.ma_nvkd) IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD,','));

    SELECT ngay_ct,ngay_admin,ma_kh,ten_kh,dien_giai,ma_bp,ma_nvkd,doanhthu
    FROM #KQ_CT ORDER BY ngay_admin,ma_kh,ma_nvkd;

    DROP TABLE IF EXISTS #TempDoanhThu_CT,#MaKH_CT,#TempDS_CT,#TempDMKH_CT,#KQ_CT;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (ngay_a, ngay_b, ma_bp or '', ds_nvkd or '', ds_kh or ''))
        data = []
        while True:
            if cur.description:
                cols = [c[0] for c in cur.description]
                if 'doanhthu' in cols:
                    for row in cur.fetchall():
                        d = dict(zip(cols, row))
                        if d.get('doanhthu') is not None: d['doanhthu'] = float(d['doanhthu'])
                        d = serialize_row(d)
                        data.append(d)
            if not cur.nextset(): break
        conn.close()
        logger.info(f"[BCCT doanhthu] Returned {len(data)} rows")
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[BCCT doanhthu] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────
# API: Export Excel
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

    if not rows:
        return jsonify({'success': False, 'error': 'Không có dữ liệu'}), 400

    max_nv_depth = 0
    for r in rows:
        if r.get('type') == 'nv':
            max_nv_depth = max(max_nv_depth, r.get('depth', 0))
    nv_cols = max_nv_depth + 1
    kh_col = nv_cols + 1
    data_start = nv_cols + 2

    wb = Workbook()
    ws = wb.active
    ws.title = 'Chi tiết'
    FONT_NAME = 'Arial'
    BLACK = '000000'
    thin_border = Border(bottom=Side(style='thin', color='D5D9E4'), right=Side(style='thin', color='ECEEF3'))
    header_border = Border(bottom=Side(style='medium', color='A0AAC0'))
    total_border = Border(top=Side(style='medium', color='8090B0'), bottom=Side(style='medium', color='8090B0'))
    nv_bg_colors = ['B8C6F0', 'CADAF6', 'DAEAFC', 'E8F0FD', 'F0F5FE', 'F7FAFE']
    kh_bg = 'FFF8E1'  # light yellow for KH summary rows
    ds_bg = 'FFFFFF'   # white for DS detail
    dt_bg = 'F0FFF0'   # light green for DT detail

    def nv_bg(depth): return nv_bg_colors[min(depth, len(nv_bg_colors) - 1)]
    def nv_font_sz(depth): return 11 if depth == 0 else 10.5 if depth == 1 else 10

    # Header
    cur_row = 1
    ws.cell(row=1, column=1, value='NHÂN VIÊN KD')
    ws.cell(row=1, column=1).font = Font(name=FONT_NAME, bold=True, size=11, color=BLACK)
    ws.cell(row=1, column=1).fill = PatternFill('solid', fgColor='D0D8ED')
    ws.cell(row=1, column=1).alignment = Alignment(vertical='center')
    ws.cell(row=1, column=1).border = header_border
    for c in range(2, nv_cols + 1):
        cell = ws.cell(row=1, column=c, value='')
        cell.fill = PatternFill('solid', fgColor='D0D8ED')
        cell.border = header_border
    kh_cell = ws.cell(row=1, column=kh_col, value='KHÁCH HÀNG')
    kh_cell.font = Font(name=FONT_NAME, bold=True, size=11, color=BLACK)
    kh_cell.fill = PatternFill('solid', fgColor='D0D8ED')
    kh_cell.alignment = Alignment(vertical='center')
    kh_cell.border = header_border
    for ci, ch in enumerate(col_headers):
        cell = ws.cell(row=1, column=data_start + ci, value=ch)
        cell.font = Font(name=FONT_NAME, bold=True, size=10, color=BLACK)
        cell.fill = PatternFill('solid', fgColor='D0D8ED')
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        cell.border = header_border
    ws.row_dimensions[1].height = 30

    # Data rows
    for row_data in rows:
        cur_row += 1
        rtype = row_data.get('type', '')
        depth = row_data.get('depth', 0)
        name = row_data.get('name', '')
        values = row_data.get('values', [])
        total_cols = data_start + len(col_headers) - 1

        if rtype == 'nv':
            nv_col_idx = min(depth, nv_cols - 1) + 1
            ws.cell(row=cur_row, column=nv_col_idx, value=name)
            bg = nv_bg(depth); sz = nv_font_sz(depth)
            for c in range(1, total_cols + 1):
                cell = ws.cell(row=cur_row, column=c)
                cell.fill = PatternFill('solid', fgColor=bg)
                cell.border = thin_border
                cell.font = Font(name=FONT_NAME, bold=True, size=sz, color=BLACK)
                cell.alignment = Alignment(vertical='center', horizontal='right' if c >= data_start else 'left')
                if c >= data_start: cell.number_format = '#,##0'
            for vi, v in enumerate(values):
                if v is not None and v != '': ws.cell(row=cur_row, column=data_start + vi, value=v)

        elif rtype == 'kh':
            ws.cell(row=cur_row, column=kh_col, value=name)
            for c in range(1, total_cols + 1):
                cell = ws.cell(row=cur_row, column=c)
                cell.fill = PatternFill('solid', fgColor=kh_bg)
                cell.border = thin_border
                cell.font = Font(name=FONT_NAME, bold=True, size=10, color='6B5B00')
                cell.alignment = Alignment(vertical='center', horizontal='right' if c >= data_start else 'left')
                if c >= data_start: cell.number_format = '#,##0'
            for vi, v in enumerate(values):
                if v is not None and v != '': ws.cell(row=cur_row, column=data_start + vi, value=v)

        elif rtype in ('ds', 'dt'):
            bg_color = ds_bg if rtype == 'ds' else dt_bg
            for c in range(1, total_cols + 1):
                cell = ws.cell(row=cur_row, column=c)
                cell.fill = PatternFill('solid', fgColor=bg_color)
                cell.border = thin_border
                cell.font = Font(name=FONT_NAME, size=9.5, color=BLACK)
                cell.alignment = Alignment(vertical='center', horizontal='right' if c >= data_start else 'left')
                if c >= data_start: cell.number_format = '#,##0'
            for vi, v in enumerate(values):
                if v is not None and v != '':
                    ws.cell(row=cur_row, column=data_start + vi, value=v)

        elif rtype == 'total':
            ws.cell(row=cur_row, column=1, value='TỔNG CỘNG')
            for c in range(1, total_cols + 1):
                cell = ws.cell(row=cur_row, column=c)
                cell.fill = PatternFill('solid', fgColor='B8C6F0')
                cell.border = total_border
                cell.font = Font(name=FONT_NAME, bold=True, size=11, color=BLACK)
                cell.alignment = Alignment(vertical='center', horizontal='right' if c >= data_start else 'left')
                if c >= data_start: cell.number_format = '#,##0'
            for vi, v in enumerate(values):
                if v is not None and v != '': ws.cell(row=cur_row, column=data_start + vi, value=v)

        ws.row_dimensions[cur_row].height = 18

    for c in range(1, nv_cols + 1):
        ws.column_dimensions[get_column_letter(c)].width = 5
    ws.column_dimensions[get_column_letter(kh_col)].width = 28
    for ci in range(len(col_headers)):
        ws.column_dimensions[get_column_letter(data_start + ci)].width = 16
    ws.freeze_panes = ws.cell(row=2, column=data_start)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    now = datetime.now()
    filename = f'BaoCaoChiTiet_{now.strftime("%Y%m%d")}.xlsx'
    return send_file(buf,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)