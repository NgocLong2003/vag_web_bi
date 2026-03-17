"""
Báo cáo Khách Hàng — Blueprint
APIs: kỳ báo cáo, hierarchy, khách hàng, công nợ, doanh số, doanh thu
Prefix: /reports/bao-cao-khach-hang/api/...
"""
from flask import Blueprint, jsonify, request, send_file
from datetime import datetime, date
import pyodbc
import logging
from config import SQLSERVER_CONFIG

logger = logging.getLogger(__name__)

bp = Blueprint('bckh', __name__,
               url_prefix='/reports/bao-cao-khach-hang',
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
    """Đảm bảo date/decimal JSON-safe"""
    for k, v in d.items():
        if isinstance(v, (datetime, date)):
            d[k] = v.isoformat()
        elif v is not None and not isinstance(v, (str, int, float, bool)):
            d[k] = str(v)
    return d


# ─────────────────────────────────────────
# CTE Hierarchy (giống baocao_kinhdoanh)
# ─────────────────────────────────────────
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


# ─────────────────────────────────────────
# API: Kỳ báo cáo
# ─────────────────────────────────────────
@bp.route('/api/ky-bao-cao')
def api_ky_bao_cao():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM ky_bao_cao ORDER BY ngay_bd_xuat_ban DESC')
        data = [serialize_row(r) for r in rows_to_dict(cur)]
        conn.close()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[ky_bao_cao] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────
# API: Hierarchy
# ─────────────────────────────────────────
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


# ─────────────────────────────────────────
# API: Khách hàng
# ─────────────────────────────────────────
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


# ─────────────────────────────────────────
# API: Công nợ (dư nợ đầu kì / cuối kì)
# ─────────────────────────────────────────
@bp.route('/api/congno', methods=['POST'])
def api_congno():
    body = request.get_json(force=True)
    ngay_cut = body.get('ngay_cut', '')
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    logger.info(f"[BCKH congno] ngay_cut={ngay_cut}, ma_bp='{ma_bp}', ds_nvkd='{ds_nvkd}', ds_kh='{ds_kh}'")

    if not ngay_cut:
        return jsonify({'success': False, 'error': 'Thiếu ngay_cut'}), 400
    try:
        dt = datetime.strptime(ngay_cut, '%Y-%m-%d')
        start_y = dt.year
    except ValueError:
        logger.error(f"[BCKH congno] ngay_cut parse failed: '{ngay_cut}'")
        return jsonify({'success': False, 'error': 'ngay_cut không hợp lệ'}), 400

    bp_param = ma_bp or ""

    sql = """
    DECLARE @NgayCut DATE=?; DECLARE @StartYear INT=?;
    DECLARE @MaBP NVARCHAR(MAX)=?; DECLARE @DSMaNVKD NVARCHAR(MAX)=?; DECLARE @DSMaKH NVARCHAR(MAX)=?;
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
      AND (@MaBP IS NULL OR @MaBP='' OR k.ma_bp IN (SELECT TRIM(value) FROM STRING_SPLIT(@MaBP,',')))
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
        logger.info(f"[BCKH congno] Returned {len(data)} rows")
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[BCKH congno] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────
# API: Doanh số (bán ra)
# ─────────────────────────────────────────
@bp.route('/api/doanhso', methods=['POST'])
def api_doanhso():
    body = request.get_json(force=True)
    ngay_a = body.get('ngay_a', '')
    ngay_b = body.get('ngay_b', '')
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    logger.info(f"[BCKH doanhso] ngay_a={ngay_a}, ngay_b={ngay_b}, ma_bp='{ma_bp}', ds_nvkd='{ds_nvkd}'")

    if not ngay_a or not ngay_b:
        return jsonify({'success': False, 'error': 'Thiếu ngay_a hoặc ngay_b'}), 400

    bp_param = ma_bp or ""

    sql = """
    DECLARE @NgayA DATE=?; DECLARE @NgayB DATE=?;
    DECLARE @MaBP NVARCHAR(MAX)=?; DECLARE @DSMaNVKD NVARCHAR(MAX)=?; DECLARE @DSMaKH NVARCHAR(MAX)=?;
    SELECT ma_kh, ma_bp,
        CASE WHEN ma_nvkd='NVQ02' AND ma_bp='VB' THEN 'NVQ03' ELSE ma_nvkd END AS ma_nvkd,
        SUM(so_luong) AS tong_so_luong, SUM(tien_nt2) AS tong_tien_nt2,
        SUM(tien_ck_nt) AS tong_tien_ck_nt, SUM(thue_gtgt_nt) AS tong_thue_gtgt_nt,
        SUM(tien_nt2-tien_ck_nt) AS tong_doanhso
    FROM BKHDBANHANG_VIEW
    WHERE ngay_ct>=@NgayA AND ngay_ct<=@NgayB AND ma_bp!='TN'
      AND (@MaBP IS NULL OR @MaBP='' OR ma_bp IN (SELECT TRIM(value) FROM STRING_SPLIT(@MaBP,',')))
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
            for k in ('tong_so_luong', 'tong_tien_nt2', 'tong_tien_ck_nt', 'tong_thue_gtgt_nt', 'tong_doanhso'):
                if d.get(k) is not None: d[k] = float(d[k])
            data.append(d)
        conn.close()
        logger.info(f"[BCKH doanhso] Returned {len(data)} rows")
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[BCKH doanhso] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────
# API: Doanh thu (thanh toán)
# ─────────────────────────────────────────
@bp.route('/api/doanhthu', methods=['POST'])
def api_doanhthu():
    body = request.get_json(force=True)
    ngay_a = body.get('ngay_a', '')
    ngay_b = body.get('ngay_b', '')
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    logger.info(f"[BCKH doanhthu] ngay_a={ngay_a}, ngay_b={ngay_b}, ma_bp='{ma_bp}', ds_nvkd='{ds_nvkd}'")

    if not ngay_a or not ngay_b:
        logger.warning(f"[BCKH doanhthu] Missing dates, skipping")
        return jsonify({'success': False, 'error': 'Thiếu ngay_a hoặc ngay_b'}), 400

    bp_param = ma_bp or ""

    sql = """
    DECLARE @NgayA DATE=?; DECLARE @NgayB DATE=?;
    DECLARE @MaBP NVARCHAR(MAX)=?; DECLARE @DSMaNVKD NVARCHAR(MAX)=?; DECLARE @DSMaKH NVARCHAR(MAX)=?;

    SELECT dt.ngay_ct,dt.ma_kh_ct,dt.ma_bp,dt.ps_co
    INTO #TempDoanhThu_DT FROM PTHUBAOCO_VIEW dt
    WHERE dt.tk_co='131' AND dt.ma_bp!='TN'
      AND ((dt.ngay_ct>='2026-01-01' AND dt.tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
        OR (dt.ngay_ct<'2026-01-01' AND dt.ma_ct='CA1'))
      AND (@MaBP IS NULL OR @MaBP='' OR dt.ma_bp IN (SELECT TRIM(value) FROM STRING_SPLIT(@MaBP,',')))
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
        dt.ma_kh_ct,dt.ma_bp,COALESCE(ds.ma_nvkd,dmkh.ma_nvkd) AS ma_nvkd,SUM(dt.ps_co) AS doanhthu
    INTO #KetQua_DT
    FROM #TempDoanhThu_DT dt
    OUTER APPLY (SELECT TOP 1 ma_nvkd FROM #TempDoanhSo_DT tds WHERE tds.ma_kh=dt.ma_kh_ct AND tds.ngay_ct<=dt.ngay_ct ORDER BY tds.ngay_ct DESC) ds
    OUTER APPLY (SELECT TOP 1 ma_nvkd FROM #TempDMKH_DT tdmkh WHERE tdmkh.ma_kh=dt.ma_kh_ct) dmkh
    WHERE @DSMaNVKD='' OR COALESCE(ds.ma_nvkd,dmkh.ma_nvkd) IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD,','))
    GROUP BY dt.ngay_ct,CASE WHEN dt.ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,dt.ngay_ct) ELSE dt.ngay_ct END,
        dt.ma_kh_ct,dt.ma_bp,COALESCE(ds.ma_nvkd,dmkh.ma_nvkd);

    SELECT ngay_ct,ngay_admin,ma_kh_ct AS ma_kh,ma_bp,ma_nvkd,doanhthu
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
        logger.info(f"[BCKH doanhthu] Returned {len(data)} rows")
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[BCKH doanhthu] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────
# API: Dư nợ trong kỳ
# Logic: bán ra - trả về - doanh thu - thưởng
# 2 khoảng ngày khác nhau:
#   - Bán ra & trả về: ngay_a_hang → ngay_b_hang (khoảng xuất bán)
#   - Doanh thu & thưởng: ngay_a_tien → ngay_b_tien (khoảng thu tiền)
# ─────────────────────────────────────────
@bp.route('/api/dunotrongky', methods=['POST'])
def api_dunotrongky():
    body = request.get_json(force=True)
    ngay_a_hang = body.get('ngay_a_hang', '')
    ngay_b_hang = body.get('ngay_b_hang', '')
    ngay_a_tien = body.get('ngay_a_tien', '')
    ngay_b_tien = body.get('ngay_b_tien', '')
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    logger.info(f"[BCKH dunotrongky] hang={ngay_a_hang}→{ngay_b_hang}, tien={ngay_a_tien}→{ngay_b_tien}, bp='{ma_bp}', nvkd='{ds_nvkd}'")

    if not ngay_a_hang or not ngay_b_hang or not ngay_a_tien or not ngay_b_tien:
        return jsonify({'success': False, 'error': 'Thiếu ngày'}), 400

    bp_param = ma_bp or ''

    sql = """
    DECLARE @NgayAHang DATE=?;
    DECLARE @NgayBHang DATE=?;
    DECLARE @NgayATien DATE=?;
    DECLARE @NgayBTien DATE=?;
    DECLARE @MaBP NVARCHAR(MAX)=?;
    DECLARE @DSMaNVKD NVARCHAR(MAX)=?;
    DECLARE @DSMaKH NVARCHAR(MAX)=?;

    -- Bán ra (SO3): ps_no - ps_co trong khoảng xuất bán
    ;WITH ban_ra AS (
        SELECT ma_kh,
               SUM(ps_no - ps_co) AS ban_ra
        FROM BANGKECHUNGTU_VIEW
        WHERE tk = '131' AND ma_ct = 'SO3'
          AND ngay_ct >= @NgayAHang AND ngay_ct <= @NgayBHang
        GROUP BY ma_kh
    ),
    -- Trả về (SO4): ps_co - ps_no trong khoảng xuất bán
    tra_ve AS (
        SELECT ma_kh,
               SUM(ps_co - ps_no) AS tra_ve
        FROM BANGKECHUNGTU_VIEW
        WHERE tk = '131' AND ma_ct = 'SO4'
          AND ngay_ct >= @NgayAHang AND ngay_ct <= @NgayBHang
        GROUP BY ma_kh
    ),
    -- Doanh thu + thưởng (không phải SO3, SO4): ps_co - ps_no trong khoảng thu tiền
    thu_tien AS (
        SELECT ma_kh,
               SUM(ps_co - ps_no) AS dt_thuong
        FROM BANGKECHUNGTU_VIEW
        WHERE tk = '131' AND ma_ct NOT IN ('SO3', 'SO4')
          AND ngay_ct >= @NgayATien AND ngay_ct <= @NgayBTien
        GROUP BY ma_kh
    ),
    -- Tổng hợp: bán ra - trả về - (doanh thu + thưởng)
    tong_hop AS (
        SELECT
            COALESCE(b.ma_kh, t.ma_kh, tt.ma_kh) AS ma_kh,
            ISNULL(b.ban_ra, 0) AS ban_ra,
            ISNULL(t.tra_ve, 0) AS tra_ve,
            ISNULL(tt.dt_thuong, 0) AS dt_thuong,
            ISNULL(b.ban_ra, 0) - ISNULL(t.tra_ve, 0) - ISNULL(tt.dt_thuong, 0) AS du_no_trong_ky
        FROM ban_ra b
        FULL OUTER JOIN tra_ve t ON b.ma_kh = t.ma_kh
        FULL OUTER JOIN thu_tien tt ON COALESCE(b.ma_kh, t.ma_kh) = tt.ma_kh
        WHERE ISNULL(b.ban_ra, 0) - ISNULL(t.tra_ve, 0) - ISNULL(tt.dt_thuong, 0) != 0
    )
    SELECT
        th.ma_kh,
        k.ten_kh,
        k.ma_bp,
        k.ma_nvkd,
        th.ban_ra,
        th.tra_ve,
        th.dt_thuong,
        th.du_no_trong_ky
    FROM tong_hop th
    LEFT JOIN (
        SELECT DISTINCT ma_kh, ten_kh, ma_bp, ma_nvkd
        FROM [dbo].[DMKHACHHANG_VIEW]
        WHERE ma_bp IS NOT NULL AND ma_bp != 'TN' AND ma_kh != 'TTT'
    ) k ON th.ma_kh = k.ma_kh
    WHERE k.ma_kh IS NOT NULL
      AND (@MaBP IS NULL OR @MaBP = '' OR k.ma_bp IN (SELECT TRIM(value) FROM STRING_SPLIT(@MaBP, ',')))
      AND (@DSMaNVKD = '' OR k.ma_nvkd IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD, ',')))
      AND (@DSMaKH = '' OR th.ma_kh IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH, ',')))
    ORDER BY th.ma_kh;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (ngay_a_hang, ngay_b_hang, ngay_a_tien, ngay_b_tien, bp_param, ds_nvkd, ds_kh))
        data = []
        for row in cur.fetchall():
            cols = [c[0] for c in cur.description]
            d = dict(zip(cols, row))
            for k in ('ban_ra', 'tra_ve', 'dt_thuong', 'du_no_trong_ky'):
                if d.get(k) is not None: d[k] = float(d[k])
            data.append(d)
        conn.close()
        logger.info(f"[BCKH dunotrongky] Returned {len(data)} rows")
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[BCKH dunotrongky] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────
# API: Dư nợ cuối kỳ
# = Công nợ tới ngay_kt_thu_tien
#   - (Bán ra lân kì - Trả lại lân kì)
# ─────────────────────────────────────────
@bp.route('/api/dunocuoiky', methods=['POST'])
def api_dunocuoiky():
    body = request.get_json(force=True)
    ngay_cut = body.get('ngay_cut', '')
    ngay_a_lk = body.get('ngay_a_lk', '')
    ngay_b_lk = body.get('ngay_b_lk', '')
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')

    logger.info(f"[BCKH dunocuoiky] cut={ngay_cut}, lk={ngay_a_lk}→{ngay_b_lk}, bp='{ma_bp}'")

    if not ngay_cut:
        return jsonify({'success': False, 'error': 'Thiếu ngay_cut'}), 400
    try:
        dt = datetime.strptime(ngay_cut, '%Y-%m-%d')
        start_y = dt.year
    except ValueError:
        return jsonify({'success': False, 'error': 'ngay_cut không hợp lệ'}), 400

    bp_param = ma_bp or ''
    has_lk = 1 if (ngay_a_lk and ngay_b_lk) else 0

    sql = """
    DECLARE @NgayCut DATE=?; DECLARE @StartYear INT=?;
    DECLARE @NgayALK DATE=?; DECLARE @NgayBLK DATE=?; DECLARE @HasLK BIT=?;
    DECLARE @MaBP NVARCHAR(MAX)=?; DECLARE @DSMaNVKD NVARCHAR(MAX)=?; DECLARE @DSMaKH NVARCHAR(MAX)=?;

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
    congno AS (
        SELECT COALESCE(s.ma_kh,p.ma_kh) AS ma_kh,
            ISNULL(s.so_du_ban_dau,0)+ISNULL(p.tong_phatsinh,0) AS du_no
        FROM so_du_dau_nam s FULL OUTER JOIN phatsinh p ON s.ma_kh=p.ma_kh
    ),
    ds_lan_ki AS (
        SELECT ma_kh,
            SUM(CASE WHEN ma_ct='SO3' THEN ps_no-ps_co ELSE 0 END) AS ban_ra_lk,
            SUM(CASE WHEN ma_ct='SO4' THEN ps_co-ps_no ELSE 0 END) AS tra_ve_lk
        FROM BANGKECHUNGTU_VIEW
        WHERE tk='131' AND ma_ct IN ('SO3','SO4')
          AND @HasLK=1 AND ngay_ct>=@NgayALK AND ngay_ct<=@NgayBLK
        GROUP BY ma_kh
    ),
    ketqua AS (
        SELECT COALESCE(c.ma_kh,d.ma_kh) AS ma_kh,
            ISNULL(c.du_no,0) AS du_no,
            ISNULL(d.ban_ra_lk,0) AS ban_ra_lk,
            ISNULL(d.tra_ve_lk,0) AS tra_ve_lk,
            ISNULL(c.du_no,0) - (ISNULL(d.ban_ra_lk,0) - ISNULL(d.tra_ve_lk,0)) AS du_no_cuoi_ky
        FROM congno c FULL OUTER JOIN ds_lan_ki d ON c.ma_kh=d.ma_kh
        WHERE ISNULL(c.du_no,0) - (ISNULL(d.ban_ra_lk,0) - ISNULL(d.tra_ve_lk,0)) != 0
    )
    SELECT kq.ma_kh,k.ten_kh,k.ma_bp,k.ma_nvkd,kq.du_no,kq.ban_ra_lk,kq.tra_ve_lk,kq.du_no_cuoi_ky
    FROM ketqua kq
    LEFT JOIN (SELECT DISTINCT ma_kh,ten_kh,ma_bp,ma_nvkd FROM DMKHACHHANG_VIEW WHERE ma_bp IS NOT NULL AND ma_bp!='TN' AND ma_kh!='TTT') k ON kq.ma_kh=k.ma_kh
    WHERE k.ma_kh IS NOT NULL
      AND (@MaBP IS NULL OR @MaBP='' OR k.ma_bp IN (SELECT TRIM(value) FROM STRING_SPLIT(@MaBP,',')))
      AND (@DSMaNVKD='' OR k.ma_nvkd IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD,',')))
      AND (@DSMaKH='' OR kq.ma_kh IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH,',')))
    ORDER BY kq.ma_kh;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (ngay_cut, start_y, ngay_a_lk or None, ngay_b_lk or None,
                          has_lk, bp_param, ds_nvkd, ds_kh))
        data = []
        for row in cur.fetchall():
            cols = [c[0] for c in cur.description]
            d = dict(zip(cols, row))
            for fld in ('du_no', 'ban_ra_lk', 'tra_ve_lk', 'du_no_cuoi_ky'):
                if d.get(fld) is not None: d[fld] = float(d[fld])
            data.append(d)
        conn.close()
        logger.info(f"[BCKH dunocuoiky] Returned {len(data)} rows")
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[BCKH dunocuoiky] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────
# API: Chi tiết doanh số (cho modal lịch sử)
# ─────────────────────────────────────────
@bp.route('/api/doanhso_chitiet', methods=['POST'])
def api_doanhso_chitiet():
    body = request.get_json(force=True)
    ngay_a = body.get('ngay_a', '')
    ngay_b = body.get('ngay_b', '')
    ma_kh = body.get('ma_kh', '')
    if not ngay_a or not ngay_b or not ma_kh:
        return jsonify({'success': False, 'error': 'Thiếu tham số'}), 400
    sql = """
    DECLARE @NgayA DATE=?; DECLARE @NgayB DATE=?; DECLARE @MaKH NVARCHAR(50)=?;
    SELECT ngay_ct,
        CASE WHEN ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,ngay_ct) ELSE ngay_ct END AS ngay_admin,
        ma_kh, ma_vt, ten_vt, dvt, so_luong, gia_nt2, tien_nt2, tien_ck_nt, thue_gtgt_nt,
        tien_nt2-tien_ck_nt AS doanhso
    FROM BKHDBANHANG_VIEW
    WHERE ma_kh=@MaKH AND ma_bp!='TN'
      AND CASE WHEN ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,ngay_ct) ELSE ngay_ct END>=@NgayA
      AND CASE WHEN ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,ngay_ct) ELSE ngay_ct END<=@NgayB
    ORDER BY ngay_ct;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (ngay_a, ngay_b, ma_kh))
        data = []
        for row in cur.fetchall():
            cols = [c[0] for c in cur.description]
            d = dict(zip(cols, row))
            for fld in ('so_luong', 'gia_nt2', 'tien_nt2', 'tien_ck_nt', 'thue_gtgt_nt', 'doanhso'):
                if d.get(fld) is not None: d[fld] = float(d[fld])
            d = serialize_row(d)
            data.append(d)
        conn.close()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[BCKH ds_chitiet] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────
# API: Chi tiết doanh thu (cho modal lịch sử)
# ─────────────────────────────────────────
@bp.route('/api/doanhthu_chitiet', methods=['POST'])
def api_doanhthu_chitiet():
    body = request.get_json(force=True)
    ngay_a = body.get('ngay_a', '')
    ngay_b = body.get('ngay_b', '')
    ma_kh = body.get('ma_kh', '')
    if not ngay_a or not ngay_b or not ma_kh:
        return jsonify({'success': False, 'error': 'Thiếu tham số'}), 400
    sql = """
    DECLARE @NgayA DATE=?; DECLARE @NgayB DATE=?; DECLARE @MaKH NVARCHAR(50)=?;
    SELECT dt.ngay_ct,
        CASE WHEN dt.ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,dt.ngay_ct) ELSE dt.ngay_ct END AS ngay_admin,
        dt.ma_kh_ct AS ma_kh, dt.ten_kh, dt.dien_giai, dt.ma_bp, dt.ps_co AS doanhthu
    FROM PTHUBAOCO_VIEW dt
    WHERE dt.tk_co='131' AND dt.ma_bp!='TN' AND dt.ma_kh_ct=@MaKH
      AND ((dt.ngay_ct>='2026-01-01' AND dt.tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
        OR (dt.ngay_ct<'2026-01-01' AND dt.ma_ct='CA1'))
      AND dt.ngay_ct>=@NgayA AND dt.ngay_ct<=@NgayB
    ORDER BY dt.ngay_ct;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, (ngay_a, ngay_b, ma_kh))
        data = []
        for row in cur.fetchall():
            cols = [c[0] for c in cur.description]
            d = dict(zip(cols, row))
            if d.get('doanhthu') is not None: d['doanhthu'] = float(d['doanhthu'])
            d = serialize_row(d)
            data.append(d)
        conn.close()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"[BCKH dt_chitiet] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
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
    ws.title = 'Báo cáo KH'
    FONT_NAME = 'Arial'
    BLACK = '000000'
    thin_border = Border(bottom=Side(style='thin', color='D5D9E4'), right=Side(style='thin', color='ECEEF3'))
    header_border = Border(bottom=Side(style='medium', color='A0AAC0'))
    total_border = Border(top=Side(style='medium', color='8090B0'), bottom=Side(style='medium', color='8090B0'))
    nv_bg_colors = ['B8C6F0', 'CADAF6', 'DAEAFC', 'E8F0FD', 'F0F5FE', 'F7FAFE']
    def nv_bg(depth): return nv_bg_colors[min(depth, len(nv_bg_colors) - 1)]
    def nv_font_sz(depth): return 11 if depth == 0 else 10.5 if depth == 1 else 10

    cur_row = 1
    ws.cell(row=1, column=1, value='NHÂN VIÊN KINH DOANH')
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
        cell.font = Font(name=FONT_NAME, bold=True, size=11, color=BLACK)
        cell.fill = PatternFill('solid', fgColor='D0D8ED')
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        cell.border = header_border
    ws.row_dimensions[1].height = 42

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
                if c >= data_start:
                    cell.font = Font(name=FONT_NAME, bold=True, size=sz, color=BLACK)
                    cell.alignment = Alignment(vertical='center', horizontal='right')
                    cell.number_format = '#,##0'
                else:
                    cell.font = Font(name=FONT_NAME, bold=True, size=sz, color=BLACK)
                    cell.alignment = Alignment(vertical='center')
            for vi, v in enumerate(values):
                if v is not None and v != '': ws.cell(row=cur_row, column=data_start + vi, value=v)

        elif rtype == 'kh':
            ws.cell(row=cur_row, column=kh_col, value=name)
            for c in range(1, total_cols + 1):
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
                if v is not None and v != '': ws.cell(row=cur_row, column=data_start + vi, value=v)

        elif rtype == 'total':
            ws.cell(row=cur_row, column=1, value='TỔNG CỘNG')
            for c in range(1, total_cols + 1):
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
                if v is not None and v != '': ws.cell(row=cur_row, column=data_start + vi, value=v)

        ws.row_dimensions[cur_row].height = 20

    for c in range(1, nv_cols + 1):
        ws.column_dimensions[get_column_letter(c)].width = 6
    ws.column_dimensions[get_column_letter(kh_col)].width = 32
    for ci in range(len(col_headers)):
        ws.column_dimensions[get_column_letter(data_start + ci)].width = 22
    ws.freeze_panes = ws.cell(row=2, column=data_start)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    now = datetime.now()
    filename = f'BaoCaoKH{"_" + kbc_name if kbc_name else ""}_{now.strftime("%Y%m%d")}.xlsx'
    return send_file(buf,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)