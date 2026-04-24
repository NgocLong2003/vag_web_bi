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


@bp.route('/api/analysis', methods=['POST'])
def api_analysis():
    """
    Bảng phân tích so sánh kỳ.
    Body: thang, nam, ma_bp, ds_nvkd, ds_kh, ds_vt, ds_kho,
          ten_plkv1, ten_plkv2, ten_plkv3,
          dimensions (list of field names to group by)
    Returns: rows grouped by selected dimensions, with current month value
             + comparisons (prev month, same month last year, avg 2/3/6/12 months)
    """
    body = request.get_json(force=True)
    thang = int(body.get('thang', 0))
    nam = int(body.get('nam', 0))
    ma_bp = body.get('ma_bp', '')
    ds_nvkd = body.get('ds_nvkd', '')
    ds_kh = body.get('ds_kh', '')
    ds_vt = body.get('ds_vt', '')
    ds_kho = body.get('ds_kho', '')
    ten_plkv1 = body.get('ten_plkv1', '')
    ten_plkv2 = body.get('ten_plkv2', '')
    ten_plkv3 = body.get('ten_plkv3', '')
    dimensions = body.get('dimensions', ['ma_kh'])

    if not thang or not nam:
        return api_response(ok=False, error='Thiếu tháng/năm', status_code=400)

    try:
        store = get_store()

        # Build date range: 12 months back from target month
        from datetime import date
        from dateutil.relativedelta import relativedelta

        target = date(nam, thang, 1)
        start_12m = target - relativedelta(months=12)
        end_of_month = (target + relativedelta(months=1)) - relativedelta(days=1)

        # Map dimension fields to SQL expressions
        DIM_SQL = {
            'ma_kh': "b.ma_kh",
            'ma_bp': "b.ma_bp",
            'ma_kho': "b.ma_kho",
            'ma_nvkd': "CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03' ELSE b.ma_nvkd END",
            'ma_vt': "b.ma_vt",
            'ten_plkv1': "COALESCE(kh.ten_plkh1, '')",
            'ten_plkv2': "COALESCE(kh.ten_plkh2, '')",
            'ten_plkv3': "COALESCE(kh.ten_plkh3, '')",
        }

        # Validate dimensions
        valid_dims = [d for d in dimensions if d in DIM_SQL]
        if not valid_dims:
            valid_dims = ['ma_kh']

        dim_exprs = [DIM_SQL[d] + ' AS ' + d for d in valid_dims]
        dim_group = [DIM_SQL[d] for d in valid_dims]

        # Also select name columns for display
        name_cols = []
        if 'ma_kh' in valid_dims:
            name_cols.append("MAX(kh.ten_kh) AS ten_kh")
        if 'ma_vt' in valid_dims:
            name_cols.append("MAX(b.ten_vt) AS ten_vt")
        if 'ma_nvkd' in valid_dims:
            name_cols.append("""MAX(CASE WHEN nv.ma_nvkd IS NOT NULL THEN nv.ten_nvkd ELSE '' END) AS ten_nvkd""")

        name_select = (', ' + ', '.join(name_cols)) if name_cols else ''

        # Need NV join?
        nv_join = ""
        if 'ma_nvkd' in valid_dims:
            nv_join = """LEFT JOIN (SELECT DISTINCT ma_nvkd, ten_nvkd FROM DMNHANVIENKD) nv
                         ON (CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03' ELSE b.ma_nvkd END) = nv.ma_nvkd"""

        sql = f"""
            SELECT
                YEAR(b.ngay_ct) AS nam,
                MONTH(b.ngay_ct) AS thang,
                {', '.join(dim_exprs)}
                {name_select},
                SUM(b.so_luong) AS tong_so_luong,
                SUM(b.tien_nt2 - b.tien_ck_nt) AS tong_doanhso
            FROM BKHDBANHANG b
            LEFT JOIN DMKHACHHANG kh ON b.ma_kh = kh.ma_kh
            {nv_join}
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
            GROUP BY YEAR(b.ngay_ct), MONTH(b.ngay_ct), {', '.join(dim_group)}
            ORDER BY {', '.join(dim_group)}
        """

        rows = store.query(sql, [
            start_12m.strftime('%Y-%m-%d'), end_of_month.strftime('%Y-%m-%d'),
            ma_bp or '', ds_nvkd or '', ds_kh or '', ds_vt or '',
            ds_kho or '', ten_plkv1 or '', ten_plkv2 or '', ten_plkv3 or ''
        ])

        # Build aggregation: dim_key → {month_key → value}
        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(lambda: {'ds': 0, 'sl': 0}))
        dim_names = {}  # dim_key → display names

        for r in rows:
            key_parts = [str(r.get(d, '')) for d in valid_dims]
            dim_key = '||'.join(key_parts)
            month_key = f"{r['nam']}-{int(r['thang']):02d}"
            agg[dim_key][month_key]['ds'] += float(r.get('tong_doanhso') or 0)
            agg[dim_key][month_key]['sl'] += float(r.get('tong_so_luong') or 0)

            if dim_key not in dim_names:
                names = {}
                for d in valid_dims:
                    names[d] = str(r.get(d, ''))
                if 'ma_kh' in valid_dims and r.get('ten_kh'):
                    names['ten_kh'] = r['ten_kh']
                if 'ma_vt' in valid_dims and r.get('ten_vt'):
                    names['ten_vt'] = r['ten_vt']
                if 'ma_nvkd' in valid_dims and r.get('ten_nvkd'):
                    names['ten_nvkd'] = r['ten_nvkd']
                dim_names[dim_key] = names

        # Calculate comparisons for each dim_key
        target_key = f"{nam}-{thang:02d}"

        # Previous months
        def month_key_offset(base_year, base_month, offset):
            from datetime import date
            d = date(base_year, base_month, 1) - relativedelta(months=offset)
            return f"{d.year}-{d.month:02d}"

        prev_1 = month_key_offset(nam, thang, 1)
        same_ly = month_key_offset(nam, thang, 12)

        avg_ranges = {
            'avg3': [month_key_offset(nam, thang, i) for i in range(1, 4)],
            'avg6': [month_key_offset(nam, thang, i) for i in range(1, 7)],
            'avg12': [month_key_offset(nam, thang, i) for i in range(1, 13)],
        }

        result = []
        total_current_ds = sum(agg[dk][target_key]['ds'] for dk in agg)
        total_prev_ds = sum(agg[dk][prev_1]['ds'] for dk in agg)
        total_delta = total_current_ds - total_prev_ds

        for dim_key, months_data in agg.items():
            current = months_data.get(target_key, {'ds': 0, 'sl': 0})
            prev = months_data.get(prev_1, {'ds': 0, 'sl': 0})
            same_last_year = months_data.get(same_ly, {'ds': 0, 'sl': 0})

            row = {
                'dims': dim_names.get(dim_key, {}),
                'current_ds': current['ds'],
                'current_sl': current['sl'],
                'prev1_ds': prev['ds'],
                'same_ly_ds': same_last_year['ds'],
            }

            # Delta vs prev month
            row['delta_prev1'] = current['ds'] - prev['ds']
            row['pct_prev1'] = round((current['ds'] / prev['ds'] - 1) * 100, 1) if prev['ds'] else None

            # Delta vs same month last year
            row['delta_ly'] = current['ds'] - same_last_year['ds']
            row['pct_ly'] = round((current['ds'] / same_last_year['ds'] - 1) * 100, 1) if same_last_year['ds'] else None

            # Share of total current month revenue
            row['share_pct'] = round(current['ds'] / total_current_ds * 100, 1) if total_current_ds else None

            # Averages
            for avg_name, avg_keys in avg_ranges.items():
                vals = [months_data[k]['ds'] for k in avg_keys if k in months_data and months_data[k]['ds']]
                avg_val = sum(vals) / len(vals) if vals else 0
                row[f'{avg_name}_ds'] = round(avg_val)
                row[f'delta_{avg_name}'] = current['ds'] - avg_val
                row[f'pct_{avg_name}'] = round((current['ds'] / avg_val - 1) * 100, 1) if avg_val else None

            # Include if has any activity in any period
            has_activity = current['ds'] or prev['ds'] or same_last_year['ds']
            if has_activity:
                result.append(row)

        # Sort by absolute delta vs prev month (largest impact first)
        result.sort(key=lambda r: abs(r.get('delta_prev1', 0)), reverse=True)

        return api_response(ok=True, data=result, count=len(result),
                            meta={'thang': thang, 'nam': nam, 'dimensions': valid_dims,
                                  'total_current': total_current_ds, 'total_delta': total_delta})

    except Exception as e:
        logger.error(f'[ptsp] analysis error: {e}')
        import traceback
        traceback.print_exc()
        return api_response(ok=False, error=str(e))