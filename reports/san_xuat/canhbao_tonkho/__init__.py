"""
reports/san_xuat/canhbao_tonkho/__init__.py — Cảnh báo tồn kho
Datasource: sanxuat (SQL Server realtime)
Gọi stored procedure asINRptCB_DMAT_Flat

SP chạy lâu (30-60s) nên tạo connection riêng với timeout dài,
không dùng pool mặc định (pool=15s).
"""
from flask import Blueprint, request
from api_logger import api_response
from datetime import date, datetime as dt
from decimal import Decimal
import logging
import pyodbc

logger = logging.getLogger(__name__)

bp = Blueprint('cbtk', __name__, url_prefix='/reports/canh-bao-ton-kho')

# Command timeout (seconds) cho SP nặng
SP_TIMEOUT = 180


def _get_conn():
    """Tạo connection mới với timeout dài, không dùng pool."""
    from config import DATASOURCES
    c = DATASOURCES.get('sanxuat')
    if not c:
        raise RuntimeError("DATASOURCES['sanxuat'] chưa cấu hình")
    conn = pyodbc.connect(
        f"DRIVER={{{c['driver']}}};SERVER={c['server']},{c['port']};"
        f"DATABASE={c['database']};UID={c['username']};PWD={c['password']};"
        "TrustServerCertificate=yes;Connect Timeout=30;",
        timeout=30,
        autocommit=True
    )
    conn.timeout = SP_TIMEOUT
    return conn


def _serialize(row_dict):
    """Convert Decimal/datetime → JSON-safe."""
    for k, v in row_dict.items():
        if isinstance(v, Decimal):
            row_dict[k] = float(v)
        elif isinstance(v, dt):
            row_dict[k] = v.isoformat()
    return row_dict


@bp.route('/api/data')
def api_data():
    """
    Gọi SP asINRptCB_DMAT_Flat.
    Query params:
      - ngay: YYYY-MM-DD (default: hôm nay)
      - dk_ck: 1 hoặc 2 (default: 2)
    """
    ngay = request.args.get('ngay', '').strip()
    dk_ck = request.args.get('dk_ck', '2').strip()

    if not ngay:
        ngay = date.today().isoformat()

    try:
        dk_ck_int = int(dk_ck)
        if dk_ck_int not in (1, 2):
            dk_ck_int = 2
    except:
        dk_ck_int = 2

    conn = None
    t0 = dt.now()
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SET NOCOUNT ON; EXEC asINRptCB_DMAT_Flat @pNgay=?, @pDk_Ck=?",
            [ngay, dk_ck_int]
        )

        while cur.description is None:
            if not cur.nextset():
                break

        if cur.description is None:
            return api_response(ok=True, rows=[], count=0,
                                ngay=ngay, dk_ck=dk_ck_int,
                                meta={'ngay': ngay, 'dk_ck': dk_ck_int})

        columns = [d[0] for d in cur.description]
        rows_raw = cur.fetchall()

        rows = []
        for r in rows_raw:
            d = _serialize(dict(zip(columns, r)))
            for k in ('so_luong', 'tam_nhap', 'ton_kho_thuc', 'sl_antoan', 'chenh_lech'):
                v = d.get(k)
                if v is None or v == '':
                    d[k] = 0.0
                else:
                    try:
                        d[k] = float(v)
                    except:
                        d[k] = 0.0
            rows.append(d)

        elapsed = (dt.now() - t0).total_seconds()
        logger.info(f"[cbtk] SP trả {len(rows)} dòng trong {elapsed:.1f}s (ngay={ngay}, dk_ck={dk_ck_int})")

        return api_response(ok=True, rows=rows,
                            ngay=ngay, dk_ck=dk_ck_int,
                            elapsed_ms=int(elapsed * 1000),
                            meta={'ngay': ngay, 'dk_ck': dk_ck_int})

    except pyodbc.OperationalError as e:
        elapsed = (dt.now() - t0).total_seconds()
        logger.error(f'[cbtk] Timeout/OperationalError sau {elapsed:.1f}s: {e}')
        return api_response(
            ok=False,
            error=f'SP chạy quá lâu (>{SP_TIMEOUT}s) hoặc mất kết nối. Thử lại sau vài giây.',
            meta={'ngay': ngay, 'dk_ck': dk_ck_int}
        )
    except Exception as e:
        logger.exception('[cbtk] Data error')
        return api_response(ok=False, error=str(e),
                            meta={'ngay': ngay, 'dk_ck': dk_ck_int})
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


@bp.route('/api/vattu')
def api_vattu():
    """Danh sách vật tư cho autocomplete."""
    try:
        from datasource import get_ds
        ds = get_ds('sanxuat')
        rows = ds.query("""
            SELECT DISTINCT ma_vt, ten_vt, dvt
            FROM [AE1213VietAnhDATA].[dbo].[DMHANGHOA_VIEW]
            ORDER BY ma_vt
        """)
        return api_response(ok=True, items=rows, count=len(rows))
    except Exception as e:
        logger.error(f'[cbtk] vattu error: {e}')
        return api_response(ok=False, error=str(e))