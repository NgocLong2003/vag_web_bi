"""
Báo cáo Kinh Doanh — Blueprint
Converted from standalone app_bckd.py
API prefix: /reports/bao-cao-kinh-doanh/api/...
"""
from flask import Blueprint, jsonify, request, send_file, render_template
from datetime import datetime, date
import pyodbc
import logging
from config import SQLSERVER_CONFIG

logger = logging.getLogger(__name__)

bp = Blueprint('bckd', __name__,
               url_prefix='/reports/bao-cao-kinh-doanh',
               template_folder='templates')


# ─────────────────────────────────────────────
#  DB Connection (dùng config chung)
# ─────────────────────────────────────────────
def get_connection():
    c = SQLSERVER_CONFIG
    return pyodbc.connect(
        f"DRIVER={{{c['driver']}}};SERVER={c['server']},{c['port']};"
        f"DATABASE={c['database']};UID={c['username']};PWD={c['password']};"
        "TrustServerCertificate=yes;Connect Timeout=30;")


def rows_to_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ─────────────────────────────────────────────
#  CTE Hierarchy
# ─────────────────────────────────────────────
HIERARCHY_CTE = """
    NV_BASE AS (
        SELECT ma_nvkd,
               CASE
               WHEN ma_nvkd = 'DTD01' THEN 'TVV01'
               WHEN ma_nvkd = 'PQT01' THEN 'TVV01'
               WHEN ma_nvkd = 'BCT02' THEN 'TVV01'
               WHEN ma_nvkd = 'NTT02' THEN 'TVV01'
               WHEN ma_nvkd = 'NVH02' THEN 'TVV01'
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


# ─────────────────────────────────────────────
#  API: Hierarchy
# ─────────────────────────────────────────────
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
        logger.error(f"[hierarchy] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────────
#  API: Khách hàng
# ─────────────────────────────────────────────
@bp.route('/api/khachhang')
def api_khachhang():
    sql = """
    SELECT DISTINCT ma_kh, ten_kh, ma_bp, ma_nvkd
    FROM DMKHACHHANG_VIEW
    WHERE ma_bp IS NOT NULL AND ma_bp != 'TN' AND ma_kh != 'TTT'
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql)
        data = rows_to_dict(cur)
        conn.close()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[khachhang] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────────
#  API: Công nợ
# ─────────────────────────────────────────────
@bp.route('/api/congno', methods=['POST'])
def api_congno():
    body = request.get_json(force=True)
    ngay_cut = body.get('ngay_cut', '')
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    if not ngay_cut:
        return jsonify({'success': False, 'error': 'Thiếu ngay_cut'}), 400
    try:
        dt = datetime.strptime(ngay_cut, '%Y-%m-%d')
        start_y = dt.year
    except ValueError:
        return jsonify({'success': False, 'error': 'ngay_cut không hợp lệ'}), 400

    bp_param = None if not ma_bp else ma_bp

    sql = """
    DECLARE @NgayCut DATE=?; DECLARE @StartYear INT=?;
    DECLARE @MaBP NVARCHAR(50)=?; DECLARE @DSMaNVKD NVARCHAR(MAX)=?; DECLARE @DSMaKH NVARCHAR(MAX)=?;
    ;WITH
    so_du_dau_nam AS (
        SELECT COALESCE(d.ma_kh,m.ma_kh) AS ma_kh,
            ISNULL(d.so_du,0)+ISNULL(m.ps_mung1,0) AS so_du_ban_dau
        FROM (SELECT ma_kh,SUM(du_no-du_co) AS so_du FROM CONGNOKHDK_VIEW WHERE nam=@StartYear AND tk='131' GROUP BY ma_kh) d
        FULL OUTER JOIN (SELECT ma_kh,SUM(ps_no-ps_co) AS ps_mung1 FROM BANGKECHUNGTU_VIEW WHERE tk='131' AND ngay_ct=DATEFROMPARTS(@StartYear,1,1) GROUP BY ma_kh) m ON d.ma_kh=m.ma_kh
    ),
    phatsinh AS (
        SELECT ma_kh,SUM(ps_no-ps_co) AS tong_phatsinh FROM BANGKECHUNGTU_VIEW
        WHERE tk='131' AND ngay_ct>DATEFROMPARTS(@StartYear,1,1) AND ngay_ct<=@NgayCut GROUP BY ma_kh
    ),
    congno_fact AS (
        SELECT COALESCE(s.ma_kh,p.ma_kh) AS ma_kh,
            ISNULL(s.so_du_ban_dau,0) AS so_du_ban_dau, ISNULL(p.tong_phatsinh,0) AS tong_phatsinh,
            ISNULL(s.so_du_ban_dau,0)+ISNULL(p.tong_phatsinh,0) AS du_no_ck
        FROM so_du_dau_nam s FULL OUTER JOIN phatsinh p ON s.ma_kh=p.ma_kh
        WHERE ISNULL(s.so_du_ban_dau,0)+ISNULL(p.tong_phatsinh,0)!=0
    )
    SELECT cf.ma_kh,k.ten_kh,k.ma_bp,k.ma_nvkd,cf.so_du_ban_dau,cf.tong_phatsinh,cf.du_no_ck
    FROM congno_fact cf
    LEFT JOIN (SELECT DISTINCT ma_kh,ten_kh,ma_bp,ma_nvkd FROM DMKHACHHANG_VIEW WHERE ma_bp IS NOT NULL AND ma_bp!='TN' AND ma_kh!='TTT') k ON cf.ma_kh=k.ma_kh
    WHERE k.ma_kh IS NOT NULL
      AND (@MaBP IS NULL OR @MaBP='' OR k.ma_bp=@MaBP)
      AND (@DSMaNVKD='' OR k.ma_nvkd IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD,',')))
      AND (@DSMaKH='' OR cf.ma_kh IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH,',')))
    ORDER BY cf.ma_kh;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (ngay_cut, start_y, bp_param, ds_nvkd, ds_kh))
        data = []
        for row in cur.fetchall():
            cols = [c[0] for c in cur.description]
            d = dict(zip(cols, row))
            for k in ('so_du_ban_dau', 'tong_phatsinh', 'du_no_ck'):
                if d.get(k) is not None: d[k] = float(d[k])
            data.append(d)
        conn.close()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[congno] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────────
#  API: Doanh số
# ─────────────────────────────────────────────
@bp.route('/api/doanhso', methods=['POST'])
def api_doanhso():
    body = request.get_json(force=True)
    ngay_a = body.get('ngay_a', '')
    ngay_b = body.get('ngay_b', '')
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    if not ngay_a or not ngay_b:
        return jsonify({'success': False, 'error': 'Thiếu ngay_a hoặc ngay_b'}), 400

    bp_param = None if not ma_bp else ma_bp

    sql = """
    DECLARE @NgayA DATE=?; DECLARE @NgayB DATE=?;
    DECLARE @MaBP NVARCHAR(50)=?; DECLARE @DSMaNVKD NVARCHAR(MAX)=?; DECLARE @DSMaKH NVARCHAR(MAX)=?;
    SELECT ma_kh, ma_bp,
        CASE WHEN ma_nvkd='NVQ02' AND ma_bp='VB' THEN 'NVQ03' ELSE ma_nvkd END AS ma_nvkd,
        SUM(so_luong) AS tong_so_luong, SUM(tien_nt2) AS tong_tien_nt2,
        SUM(tien_ck_nt) AS tong_tien_ck_nt, SUM(thue_gtgt_nt) AS tong_thue_gtgt_nt,
        SUM(tien_nt2-tien_ck_nt) AS tong_doanhso
    FROM BKHDBANHANG_VIEW
    WHERE ngay_ct>=@NgayA AND ngay_ct<=@NgayB AND ma_bp!='TN'
      AND (@MaBP IS NULL OR @MaBP='' OR ma_bp=@MaBP)
      AND (@DSMaKH='' OR ma_kh IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH,',')))
      AND (@DSMaNVKD='' OR CASE WHEN ma_nvkd='NVQ02' AND ma_bp='VB' THEN 'NVQ03' ELSE ma_nvkd END
           IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD,',')))
    GROUP BY ma_kh,ma_bp,CASE WHEN ma_nvkd='NVQ02' AND ma_bp='VB' THEN 'NVQ03' ELSE ma_nvkd END
    ORDER BY ma_kh,ma_nvkd;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (ngay_a, ngay_b, bp_param, ds_nvkd, ds_kh))
        data = []
        for row in cur.fetchall():
            cols = [c[0] for c in cur.description]
            d = dict(zip(cols, row))
            for k in ('tong_so_luong','tong_tien_nt2','tong_tien_ck_nt','tong_thue_gtgt_nt','tong_doanhso'):
                if d.get(k) is not None: d[k] = float(d[k])
            data.append(d)
        conn.close()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[doanhso] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────────
#  API: Doanh thu
# ─────────────────────────────────────────────
@bp.route('/api/doanhthu', methods=['POST'])
def api_doanhthu():
    body = request.get_json(force=True)
    ngay_a = body.get('ngay_a', '')
    ngay_b = body.get('ngay_b', '')
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    if not ngay_a or not ngay_b:
        return jsonify({'success': False, 'error': 'Thiếu ngay_a hoặc ngay_b'}), 400

    bp_param = None if not ma_bp else ma_bp

    sql = """
    DECLARE @NgayA DATE=?; DECLARE @NgayB DATE=?;
    DECLARE @MaBP NVARCHAR(50)=?; DECLARE @DSMaNVKD NVARCHAR(MAX)=?; DECLARE @DSMaKH NVARCHAR(MAX)=?;

    SELECT dt.ngay_ct,dt.ma_kh_ct,dt.ma_bp,dt.ps_co
    INTO #TempDoanhThu_DT FROM PTHUBAOCO_VIEW dt
    WHERE dt.tk_co='131' AND dt.ma_bp!='TN'
      AND ((dt.ngay_ct>='2026-01-01' AND dt.tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
        OR (dt.ngay_ct<'2026-01-01' AND dt.ma_ct='CA1'))
      AND (@MaBP IS NULL OR @MaBP='' OR dt.ma_bp=@MaBP)
      AND dt.ngay_ct>=@NgayA AND dt.ngay_ct<=@NgayB
      AND (@DSMaKH='' OR dt.ma_kh_ct IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH,',')));

    CREATE INDEX IX_Temp_DT_KH ON #TempDoanhThu_DT(ma_kh_ct,ngay_ct);
    SELECT DISTINCT ma_kh_ct INTO #MaKH_CanTim_DT FROM #TempDoanhThu_DT;

    SELECT ds.ma_kh,ds.ma_nvkd,ds.ngay_ct INTO #TempDoanhSo_DT
    FROM BKHDBANHANG_VIEW ds INNER JOIN #MaKH_CanTim_DT mk ON ds.ma_kh=mk.ma_kh_ct;
    CREATE INDEX IX_Temp_DS_DT ON #TempDoanhSo_DT(ma_kh,ngay_ct DESC);

    SELECT dmkh.ma_kh,dmkh.ma_nvkd INTO #TempDMKH_DT
    FROM DMKHACHHANG_VIEW dmkh INNER JOIN #MaKH_CanTim_DT mk ON dmkh.ma_kh=mk.ma_kh_ct;
    CREATE INDEX IX_Temp_DMKH_DT ON #TempDMKH_DT(ma_kh);

    SELECT dt.ngay_ct,
        CASE WHEN dt.ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,dt.ngay_ct) ELSE dt.ngay_ct END AS ngay_admin,
        YEAR(CASE WHEN dt.ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,dt.ngay_ct) ELSE dt.ngay_ct END) AS year_admin,
        MONTH(CASE WHEN dt.ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,dt.ngay_ct) ELSE dt.ngay_ct END) AS month_admin,
        dt.ma_kh_ct,dt.ma_bp,COALESCE(ds.ma_nvkd,dmkh.ma_nvkd) AS ma_nvkd,SUM(dt.ps_co) AS doanhthu
    INTO #KetQua_DT
    FROM #TempDoanhThu_DT dt
    OUTER APPLY (SELECT TOP 1 ma_nvkd FROM #TempDoanhSo_DT tds WHERE tds.ma_kh=dt.ma_kh_ct AND tds.ngay_ct<=dt.ngay_ct ORDER BY tds.ngay_ct DESC) ds
    OUTER APPLY (SELECT TOP 1 ma_nvkd FROM #TempDMKH_DT tdmkh WHERE tdmkh.ma_kh=dt.ma_kh_ct) dmkh
    WHERE @DSMaNVKD='' OR COALESCE(ds.ma_nvkd,dmkh.ma_nvkd) IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD,','))
    GROUP BY dt.ngay_ct,CASE WHEN dt.ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,dt.ngay_ct) ELSE dt.ngay_ct END,
        YEAR(CASE WHEN dt.ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,dt.ngay_ct) ELSE dt.ngay_ct END),
        MONTH(CASE WHEN dt.ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,dt.ngay_ct) ELSE dt.ngay_ct END),
        dt.ma_kh_ct,dt.ma_bp,COALESCE(ds.ma_nvkd,dmkh.ma_nvkd);

    SELECT ngay_ct,ngay_admin,year_admin,month_admin,ma_kh_ct AS ma_kh,ma_bp,ma_nvkd,doanhthu
    FROM #KetQua_DT ORDER BY ngay_admin,ma_kh_ct,ma_nvkd;

    DROP TABLE IF EXISTS #TempDoanhThu_DT;
    DROP TABLE IF EXISTS #MaKH_CanTim_DT;
    DROP TABLE IF EXISTS #TempDoanhSo_DT;
    DROP TABLE IF EXISTS #TempDMKH_DT;
    DROP TABLE IF EXISTS #KetQua_DT;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (ngay_a, ngay_b, bp_param, ds_nvkd, ds_kh))
        data = []
        while True:
            if cur.description:
                cols = [c[0] for c in cur.description]
                if 'doanhthu' in cols:
                    for row in cur.fetchall():
                        d = dict(zip(cols, row))
                        if d.get('doanhthu') is not None: d['doanhthu'] = float(d['doanhthu'])
                        data.append(d)
            if not cur.nextset(): break
        conn.close()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[doanhthu] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────────
#  API: Export Excel
# ─────────────────────────────────────────────
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
    ws.title = 'Báo cáo'
    FONT_NAME = 'Arial'
    BLACK = '000000'
    thin_border = Border(bottom=Side(style='thin', color='D5D9E4'), right=Side(style='thin', color='ECEEF3'))
    header_border = Border(bottom=Side(style='medium', color='A0AAC0'))
    total_border = Border(top=Side(style='medium', color='8090B0'), bottom=Side(style='medium', color='8090B0'))
    nv_bg_colors = ['B8C6F0','CADAF6','DAEAFC','E8F0FD','F0F5FE','F7FAFE']
    def nv_bg(depth): return nv_bg_colors[min(depth, len(nv_bg_colors)-1)]
    def nv_font_sz(depth): return 11 if depth==0 else 10.5 if depth==1 else 10

    cur_row = 1
    ws.cell(row=1, column=1, value='NHÂN VIÊN KINH DOANH')
    ws.cell(row=1, column=1).font = Font(name=FONT_NAME, bold=True, size=11, color=BLACK)
    ws.cell(row=1, column=1).fill = PatternFill('solid', fgColor='D0D8ED')
    ws.cell(row=1, column=1).alignment = Alignment(vertical='center')
    ws.cell(row=1, column=1).border = header_border
    for c in range(2, nv_cols+1):
        cell = ws.cell(row=1, column=c, value='')
        cell.fill = PatternFill('solid', fgColor='D0D8ED')
        cell.border = header_border
    kh_cell = ws.cell(row=1, column=kh_col, value='KHÁCH HÀNG')
    kh_cell.font = Font(name=FONT_NAME, bold=True, size=11, color=BLACK)
    kh_cell.fill = PatternFill('solid', fgColor='D0D8ED')
    kh_cell.alignment = Alignment(vertical='center')
    kh_cell.border = header_border
    for ci, ch in enumerate(col_headers):
        cell = ws.cell(row=1, column=data_start+ci, value=ch)
        cell.font = Font(name=FONT_NAME, bold=True, size=11, color=BLACK)
        cell.fill = PatternFill('solid', fgColor='D0D8ED')
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        cell.border = header_border
    ws.row_dimensions[1].height = 36

    for row_data in rows:
        cur_row += 1
        rtype = row_data.get('type', '')
        depth = row_data.get('depth', 0)
        name = row_data.get('name', '')
        values = row_data.get('values', [])
        total_cols = data_start + len(col_headers) - 1

        if rtype == 'nv':
            nv_col_idx = min(depth, nv_cols-1) + 1
            ws.cell(row=cur_row, column=nv_col_idx, value=name)
            bg = nv_bg(depth); sz = nv_font_sz(depth)
            for c in range(1, total_cols+1):
                cell = ws.cell(row=cur_row, column=c)
                cell.fill = PatternFill('solid', fgColor=bg)
                cell.border = thin_border
                if c >= data_start:
                    cell.font = Font(name=FONT_NAME, bold=True, size=sz, color=BLACK)
                    cell.alignment = Alignment(vertical='center', horizontal='right')
                    cell.number_format = '#,##0'
                else:
                    cell.font = Font(name=FONT_NAME, bold=True, size=sz, color=BLACK)
                    cell.alignment = Alignment(vertical='center')
            for vi, v in enumerate(values):
                if v is not None and v != '': ws.cell(row=cur_row, column=data_start+vi, value=v)

        elif rtype == 'kh':
            ws.cell(row=cur_row, column=kh_col, value=name)
            for c in range(1, total_cols+1):
                cell = ws.cell(row=cur_row, column=c)
                cell.fill = PatternFill('solid', fgColor='FFFFFF')
                cell.border = thin_border
                if c >= data_start:
                    cell.font = Font(name=FONT_NAME, size=10, color=BLACK)
                    cell.alignment = Alignment(vertical='center', horizontal='right')
                    cell.number_format = '#,##0'
                else:
                    cell.font = Font(name=FONT_NAME, size=10, color=BLACK)
                    cell.alignment = Alignment(vertical='center')
            for vi, v in enumerate(values):
                if v is not None and v != '': ws.cell(row=cur_row, column=data_start+vi, value=v)

        elif rtype == 'total':
            ws.cell(row=cur_row, column=1, value='TỔNG CỘNG')
            for c in range(1, total_cols+1):
                cell = ws.cell(row=cur_row, column=c)
                cell.fill = PatternFill('solid', fgColor='B8C6F0')
                cell.border = total_border
                if c >= data_start:
                    cell.font = Font(name=FONT_NAME, bold=True, size=11, color=BLACK)
                    cell.alignment = Alignment(vertical='center', horizontal='right')
                    cell.number_format = '#,##0'
                else:
                    cell.font = Font(name=FONT_NAME, bold=True, size=11, color=BLACK)
                    cell.alignment = Alignment(vertical='center')
            for vi, v in enumerate(values):
                if v is not None and v != '': ws.cell(row=cur_row, column=data_start+vi, value=v)

        ws.row_dimensions[cur_row].height = 20

    for c in range(1, nv_cols+1):
        ws.column_dimensions[get_column_letter(c)].width = 6
    ws.column_dimensions[get_column_letter(kh_col)].width = 32
    for ci in range(len(col_headers)):
        ws.column_dimensions[get_column_letter(data_start+ci)].width = 22
    ws.freeze_panes = ws.cell(row=2, column=data_start)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    now = datetime.now()
    bp_tag = body.get('bp', '')
    filename = f'BaoCaoKD{"_"+bp_tag if bp_tag else ""}_{now.strftime("%Y%m%d")}.xlsx'
    return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)