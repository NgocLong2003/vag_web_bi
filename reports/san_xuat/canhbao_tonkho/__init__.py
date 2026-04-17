"""
reports/san_xuat/canhbao_tonkho/__init__.py — Cảnh báo tồn kho
Datasource: sanxuat (SQL Server realtime)
Gọi stored procedure asINRptCB_DMAT_Flat
"""
from flask import Blueprint, request
from api_logger import api_response
from datetime import date, datetime as dt
from decimal import Decimal
import logging
import pyodbc

logger = logging.getLogger(__name__)

bp = Blueprint('cbtk', __name__, url_prefix='/reports/canh-bao-ton-kho')
bp.api_report = 'canh-bao-ton-kho'


SP_TIMEOUT = 180


def _get_conn():
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
    for k, v in row_dict.items():
        if isinstance(v, Decimal):
            row_dict[k] = float(v)
        elif isinstance(v, dt):
            row_dict[k] = v.isoformat()
    return row_dict


KEEP_COLS = ('ma_vt', 'ten_vt', 'tam_nhap', 'ton_kho_thuc', 'sl_antoan', 'chenh_lech', 'dang_giao')
NUM_COLS = ('tam_nhap', 'ton_kho_thuc', 'sl_antoan', 'chenh_lech', 'dang_giao')


@bp.route('/api/data')
def api_data():
    ngay = request.args.get('ngay', '').strip()
    ngay_dh1 = request.args.get('ngay_dh1', '').strip()

    if not ngay:
        ngay = date.today().isoformat()
    if not ngay_dh1:
        ngay_dh1 = '2025-01-01'

    conn = None
    t0 = dt.now()
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SET NOCOUNT ON; EXEC asINRptCB_DMAT_Flat @pNgay=?, @pNgayDH1=?",
            [ngay, ngay_dh1]
        )

        while cur.description is None:
            if not cur.nextset():
                break

        if cur.description is None:
            return api_response(ok=True, rows=[], count=0,
                                meta={'ngay': ngay, 'ngay_dh1': ngay_dh1})

        columns = [d[0] for d in cur.description]
        rows_raw = cur.fetchall()

        rows = []
        for r in rows_raw:
            d = _serialize(dict(zip(columns, r)))
            out = {}
            for k in KEEP_COLS:
                out[k] = d.get(k, '' if k in ('ma_vt', 'ten_vt') else 0.0)
            for k in NUM_COLS:
                v = out.get(k)
                if v is None or v == '':
                    out[k] = 0.0
                else:
                    try:
                        out[k] = float(v)
                    except:
                        out[k] = 0.0
            rows.append(out)

        elapsed = (dt.now() - t0).total_seconds()
        logger.info(f"[cbtk] SP trả {len(rows)} dòng trong {elapsed:.1f}s (ngay={ngay}, ngay_dh1={ngay_dh1})")

        return api_response(ok=True, rows=rows,
                            elapsed_ms=int(elapsed * 1000),
                            meta={'ngay': ngay, 'ngay_dh1': ngay_dh1})

    except pyodbc.OperationalError as e:
        elapsed = (dt.now() - t0).total_seconds()
        logger.error(f'[cbtk] Timeout/OperationalError sau {elapsed:.1f}s: {e}')
        return api_response(
            ok=False,
            error=f'SP chạy quá lâu (>{SP_TIMEOUT}s) hoặc mất kết nối. Thử lại sau vài giây.',
            meta={'ngay': ngay, 'ngay_dh1': ngay_dh1}
        )
    except Exception as e:
        logger.exception('[cbtk] Data error')
        return api_response(ok=False, error=str(e),
                            meta={'ngay': ngay, 'ngay_dh1': ngay_dh1})
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


@bp.route('/api/vattu')
def api_vattu():
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


DG_KEEP = ('ngay_dat', 'ten_kh', 'ten_nha_sx', 'dang_giao')
DG_NUM = ('dang_giao')


@bp.route('/api/danggiao')
def api_danggiao():
    """Chi tiết đơn đang giao cho 1 mã vật tư."""
    ma_vt = request.args.get('ma_vt', '').strip()
    ngay = request.args.get('ngay', '').strip()
    ngay_dh1 = request.args.get('ngay_dh1', '').strip()

    if not ma_vt:
        return api_response(ok=False, error='Thiếu mã vật tư', status_code=400)
    if not ngay:
        ngay = date.today().isoformat()
    if not ngay_dh1:
        ngay_dh1 = '2025-01-01'

    conn = None
    t0 = dt.now()
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SET NOCOUNT ON; EXEC asINRptCB_DMAT_DangGiao @pMa_vt=?, @pNgay=?, @pNgayDH1=?",
            [ma_vt, ngay, ngay_dh1]
        )

        while cur.description is None:
            if not cur.nextset():
                break

        if cur.description is None:
            return api_response(ok=True, rows=[], count=0,
                                meta={'ma_vt': ma_vt, 'ngay': ngay, 'ngay_dh1': ngay_dh1})

        columns = [d[0] for d in cur.description]
        rows_raw = cur.fetchall()

        rows = []
        for r in rows_raw:
            d = _serialize(dict(zip(columns, r)))
            out = {}
            for k in DG_KEEP:
                out[k] = d.get(k, '')
            for k in DG_NUM:
                v = out.get(k)
                if v is None or v == '':
                    out[k] = 0.0
                else:
                    try:
                        out[k] = float(v)
                    except:
                        out[k] = 0.0
            # Format ngay_dat
            nd = out.get('ngay_dat', '')
            if nd and len(str(nd)) >= 10:
                out['ngay_dat'] = str(nd)[:10]
            rows.append(out)

        elapsed = (dt.now() - t0).total_seconds()
        logger.info(f"[cbtk] DangGiao {ma_vt}: {len(rows)} dòng trong {elapsed:.1f}s")

        return api_response(ok=True, rows=rows,
                            elapsed_ms=int(elapsed * 1000),
                            meta={'ma_vt': ma_vt, 'ngay': ngay, 'ngay_dh1': ngay_dh1})

    except Exception as e:
        logger.exception('[cbtk] DangGiao error')
        return api_response(ok=False, error=str(e),
                            meta={'ma_vt': ma_vt})
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass