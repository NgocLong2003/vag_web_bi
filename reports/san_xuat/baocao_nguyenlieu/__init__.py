"""
reports/san_xuat/baocao_nguyenlieu/__init__.py — Báo cáo Nguyên Liệu Sản Xuất
Datasource: sanxuat (SQL Server realtime)
Gọi stored procedure sp_TonKho_ChiTiet_TheoThang
"""
from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('bcnl', __name__, url_prefix='/reports/bao-cao-nguyen-lieu')


@bp.route('/api/data')
def api_data():
    """Gọi SP sp_TonKho_ChiTiet_TheoThang, trả về dữ liệu nhập/xuất/tồn."""
    ma_vt = request.args.get('ma_vt', '').strip()

    if not ma_vt:
        return jsonify({'ok': True, 'rows': [], 'message': 'Chọn mã vật tư'})

    try:
        from datasource import get_ds
        ds = get_ds('sanxuat')

        sql = "SET NOCOUNT ON; EXEC sp_TonKho_ChiTiet_TheoThang @pMa_vt=?"
        rows = ds.query(sql, [ma_vt])
        return jsonify({'ok': True, 'rows': rows, 'count': len(rows)})

    except Exception as e:
        logger.error(f'bcnl data error: {e}')
        return jsonify({'ok': False, 'error': str(e)}), 500


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
        return jsonify({'ok': True, 'items': rows})

    except Exception as e:
        logger.error(f'bcnl vattu error: {e}')
        return jsonify({'ok': False, 'error': str(e)}), 500