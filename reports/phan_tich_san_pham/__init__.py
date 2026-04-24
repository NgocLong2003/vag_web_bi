"""
reports/phan_tich_san_pham/__init__.py — Phân tích sản phẩm (Dashboard)
Datasource: default (DuckDB batch)
"""
from flask import Blueprint, request, current_app
from api_logger import api_response
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('ptsp', __name__, url_prefix='/reports/phan-tich-san-pham')
bp.api_report = 'Phân tích sản phẩm'

from query_loader import load_sql


def get_store():
    return current_app.config['DUCKDB_STORE']


@bp.route('/api/data', methods=['POST'])
def api_data():
    body = request.get_json(force=True)
    ngay_a = body.get('ngay_a', '')
    ngay_b = body.get('ngay_b', '')
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')
    ds_vt = body.get('ds_vt', '')
    ds_kho = body.get('ds_kho', '')
    ten_plkv1 = body.get('ten_plkv1', '')
    ten_plkv2 = body.get('ten_plkv2', '')
    ten_plkv3 = body.get('ten_plkv3', '')

    if not ngay_a or not ngay_b:
        return api_response(ok=False, error='Thiếu ngày', status_code=400)

    try:
        store = get_store()
        sql = """
            SELECT
                YEAR(b.ngay_ct) AS nam,
                MONTH(b.ngay_ct) AS thang,
                DAY(b.ngay_ct) AS ngay,
                b.ma_vt, b.ten_vt,
                CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03'
                     ELSE b.ma_nvkd END AS ma_nvkd,
                b.ma_bp, b.ma_kh, b.ma_kho,
                SUM(b.so_luong) AS tong_so_luong,
                SUM(b.tien_nt2 - b.tien_ck_nt) AS tong_doanhso
            FROM BKHDBANHANG b
            LEFT JOIN DMKHACHHANG kh ON b.ma_kh = kh.ma_kh
            WHERE b.ngay_ct >= CAST($1 AS DATE)
              AND b.ngay_ct <= CAST($2 AS DATE)
              AND ($3 = '' OR b.ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
              AND ($4 = '' OR
                  CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03'
                       ELSE b.ma_nvkd END
                  IN (SELECT TRIM(unnest(string_split($4, ',')))))
              AND ($5 = '' OR b.ma_kh IN (SELECT TRIM(unnest(string_split($5, ',')))))
              AND ($6 = '' OR b.ma_vt IN (SELECT TRIM(unnest(string_split($6, ',')))))
              AND ($7 = '' OR b.ma_kho IN (SELECT TRIM(unnest(string_split($7, ',')))))
              AND ($8 = '' OR kh.ten_plkh1 IN (SELECT TRIM(unnest(string_split($8, ',')))))
              AND ($9 = '' OR kh.ten_plkh2 IN (SELECT TRIM(unnest(string_split($9, ',')))))
              AND ($10 = '' OR kh.ten_plkh3 IN (SELECT TRIM(unnest(string_split($10, ',')))))
            GROUP BY YEAR(b.ngay_ct), MONTH(b.ngay_ct), DAY(b.ngay_ct), b.ma_vt, b.ten_vt, b.ma_bp, b.ma_kh, b.ma_kho,
                CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03'
                     ELSE b.ma_nvkd END
            ORDER BY nam, thang, b.ma_vt
        """
        rows = store.query(sql, [
            ngay_a, ngay_b,
            ma_bp or '', ds_nvkd or '', ds_kh or '', ds_vt or '',
            ds_kho or '', ten_plkv1 or '', ten_plkv2 or '', ten_plkv3 or ''
        ])

        for r in rows:
            for k in ('tong_so_luong', 'tong_doanhso'):
                v = r.get(k)
                r[k] = float(v) if v is not None else 0.0
            r['nam'] = int(r.get('nam', 0))
            r['thang'] = int(r.get('thang', 0))
            r['ngay'] = int(r.get('ngay', 0))

        return api_response(ok=True, data=rows, count=len(rows),
                            meta={'ngay_a': ngay_a, 'ngay_b': ngay_b, 'ma_bp': ma_bp})

    except Exception as e:
        logger.error(f'[ptsp] data error: {e}')
        return api_response(ok=False, error=str(e))


@bp.route('/api/sanpham')
def api_sanpham():
    """Sản phẩm đã từng bán, JOIN DMSANPHAM + LOAISANPHAM. Filter theo ma_bp."""
    ma_bp = request.args.get('ma_bp', '').strip()
    try:
        store = get_store()
        sql = """
            SELECT DISTINCT
                b.ma_vt, b.ten_vt,
                COALESCE(d.ten_thuoc, '') AS ten_thuoc,
                COALESCE(l.ten_nhvt, '') AS ten_nhvt
            FROM BKHDBANHANG b
            LEFT JOIN DMSANPHAM d ON b.ma_vt = d.ma_vt
            LEFT JOIN LOAISANPHAM l ON b.ma_vt = l.ma_spct
            WHERE ($1 = '' OR b.ma_bp IN (SELECT TRIM(unnest(string_split($1, ',')))))
            ORDER BY b.ma_vt
        """
        rows = store.query(sql, [ma_bp or ''])
        return api_response(ok=True, items=rows, count=len(rows))
    except Exception as e:
        logger.error(f'[ptsp] sanpham error: {e}')
        return api_response(ok=False, error=str(e))


@bp.route('/api/filters')
def api_filters():
    """Distinct values cho Kho, Miền, Vùng, Tỉnh, KH — filter theo ma_bp."""
    ma_bp = request.args.get('ma_bp', '').strip()
    try:
        store = get_store()

        # Kho — từ BKHDBANHANG
        kho_sql = """
            SELECT DISTINCT ma_kho FROM BKHDBANHANG
            WHERE ma_kho IS NOT NULL AND ma_kho != ''
              AND ($1 = '' OR ma_bp IN (SELECT TRIM(unnest(string_split($1, ',')))))
            ORDER BY ma_kho
        """
        kho_rows = store.query(kho_sql, [ma_bp or ''])

        # Miền/Vùng/Tỉnh + KH — từ DMKHACHHANG, filter theo ma_bp
        kh_rows = []
        plkv1, plkv2, plkv3 = [], [], []
        try:
            kv_sql = """
                SELECT DISTINCT
                    ma_kh, ten_kh, ma_bp, ma_nvkd,
                    COALESCE(ten_plkh1, '') AS ten_plkv1,
                    COALESCE(ten_plkh2, '') AS ten_plkv2,
                    COALESCE(ten_plkh3, '') AS ten_plkv3
                FROM DMKHACHHANG
                WHERE ($1 = '' OR ma_bp IN (SELECT TRIM(unnest(string_split($1, ',')))))
                ORDER BY ma_kh
            """
            kh_rows = store.query(kv_sql, [ma_bp or ''])
            plkv1 = sorted(set(r['ten_plkv1'] for r in kh_rows if r['ten_plkv1']))
            plkv2 = sorted(set(r['ten_plkv2'] for r in kh_rows if r['ten_plkv2']))
            plkv3 = sorted(set(r['ten_plkv3'] for r in kh_rows if r['ten_plkv3']))
        except Exception as e:
            logger.warning(f'[ptsp] DMKHACHHANG query failed (table may not exist): {e}')

        return api_response(ok=True,
                            kho=[r['ma_kho'] for r in kho_rows],
                            khachhang=[{'ma_kh': r['ma_kh'], 'ten_kh': r['ten_kh'],
                                        'ten_plkv1': r['ten_plkv1'], 'ten_plkv2': r['ten_plkv2'],
                                        'ten_plkv3': r['ten_plkv3']} for r in kh_rows],
                            tinh=plkv1, vung=plkv2, mien=plkv3)

    except Exception as e:
        logger.error(f'[ptsp] filters error: {e}')
        return api_response(ok=False, error=str(e))


@bp.route('/api/hierarchy')
def api_hierarchy():
    try:
        data = get_store().query(load_sql('HIERARCHY_CTE_DUCK'))
        return api_response(ok=True, data=data, count=len(data))
    except Exception as e:
        logger.error(f'[ptsp] hierarchy error: {e}')
        return api_response(ok=False, error=str(e))


@bp.route('/api/khachhang')
def api_khachhang():
    try:
        data = get_store().query(load_sql('KHACHHANG_DUCK'))
        return api_response(ok=True, data=data, count=len(data))
    except Exception as e:
        logger.error(f'[ptsp] khachhang error: {e}')
        return api_response(ok=False, error=str(e))