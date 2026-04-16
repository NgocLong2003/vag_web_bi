"""
reports/san_xuat/canhbao_tonkho/__init__.py — Cảnh báo tồn kho
Datasource: sanxuat (SQL Server realtime)
Gọi stored procedure asINRptCB_DMAT_Flat

SP chạy lâu (30-60s) nên tạo connection riêng với timeout dài,
không dùng pool mặc định (pool=15s).
"""
from flask import Blueprint, jsonify, request
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
    # Command timeout dành cho SP nặng
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
      - dk_ck: 1 hoặc 2 (default: 1)
    """
    ngay = request.args.get('ngay', '').strip()
    dk_ck = request.args.get('dk_ck', '1').strip()

    if not ngay:
        ngay = date.today().isoformat()

    try:
        dk_ck_int = int(dk_ck)
        if dk_ck_int not in (1, 2):
            dk_ck_int = 1
    except:
        dk_ck_int = 1

    conn = None
    t0 = dt.now()
    try:
        conn = _get_conn()
        cur = conn.cursor()
        # SET NOCOUNT ON để tránh extra result sets từ row counts
        cur.execute(
            "SET NOCOUNT ON; EXEC asINRptCB_DMAT_Flat @pNgay=?, @pDk_Ck=?",
            [ngay, dk_ck_int]
        )

        # SP có thể trả nhiều result sets — lặp tới khi gặp cái có columns
        while cur.description is None:
            if not cur.nextset():
                break

        if cur.description is None:
            return jsonify({'ok': True, 'rows': [], 'count': 0, 'ngay': ngay, 'dk_ck': dk_ck_int})

        columns = [d[0] for d in cur.description]
        rows_raw = cur.fetchall()

        rows = []
        for r in rows_raw:
            d = _serialize(dict(zip(columns, r)))
            # Ép kiểu số
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

        return jsonify({
            'ok': True,
            'rows': rows,
            'count': len(rows),
            'ngay': ngay,
            'dk_ck': dk_ck_int,
            'elapsed_ms': int(elapsed * 1000),
        })

    except pyodbc.OperationalError as e:
        elapsed = (dt.now() - t0).total_seconds()
        logger.error(f'[cbtk] Timeout/OperationalError sau {elapsed:.1f}s: {e}')
        return jsonify({
            'ok': False,
            'error': f'SP chạy quá lâu (>{SP_TIMEOUT}s) hoặc mất kết nối. Thử lại sau vài giây.',
        }), 500
    except Exception as e:
        logger.exception('[cbtk] Data error')
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


@bp.route('/api/vattu')
def api_vattu():
    """Danh sách vật tư cho autocomplete (giống baocao_nguyenlieu)."""
    try:
        from datasource import get_ds
        ds = get_ds('sanxuat')
        rows = ds.query("""
            SELECT DISTINCT ma_vt, ten_vt, dvt
            FROM [AE1213VietAnhDATA].[dbo].[DMHANGHOA_VIEW]
            ORDER BY ma_vt
        """)
        return jsonify({'ok': True, 'items': rows})
    except Exception as e:
        logger.error(f'[cbtk] vattu error: {e}')
        return jsonify({'ok': False, 'error': str(e)}), 500