"""
reports/san_xuat/baocao_nguyenlieu/__init__.py — Báo cáo Nguyên Liệu Sản Xuất
Datasource: sanxuat (SQL Server realtime)
Gọi stored procedure sp_TonKho_ChiTiet_TheoThang
"""
from flask import Blueprint, jsonify, request, send_file
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


@bp.route('/api/sanpham')
def api_sanpham():
    """Gọi SP sp_TonKho_NXT_TheoNVL — NXT của sản phẩm chứa nguyên liệu."""
    ma_nvl = request.args.get('ma_nvl', '').strip()
    if not ma_nvl:
        return jsonify({'ok': True, 'rows': []})

    try:
        from datasource import get_ds
        ds = get_ds('sanxuat')

        sql = "SET NOCOUNT ON; EXEC sp_TonKho_NXT_TheoNVL @pMa_nvl=?"
        rows = ds.query(sql, [ma_nvl])
        return jsonify({'ok': True, 'rows': rows, 'count': len(rows)})

    except Exception as e:
        logger.error(f'bcnl sanpham error: {e}')
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/export-xuat')
def api_export_xuat():
    """Xuất Excel bảng Xuất NVL + thành phẩm đang mở."""
    ma_vt = request.args.get('ma_vt', '').strip()
    incl_xuatle = request.args.get('xuatle', '0') == '1'
    # Danh sách mã thành phẩm đang mở (comma-separated)
    sp_codes = request.args.get('sp', '').strip()

    if not ma_vt:
        return jsonify({'ok': False, 'error': 'Chưa chọn mã vật tư'}), 400

    try:
        from datasource import get_ds
        ds = get_ds('sanxuat')

        sql = "SET NOCOUNT ON; EXEC sp_TonKho_ChiTiet_TheoThang @pMa_vt=?"
        rows = ds.query(sql, [ma_vt])

        if not rows:
            return jsonify({'ok': False, 'error': 'Không có dữ liệu'}), 404

        # Lấy tên + đvt
        ten_vt, dvt = '', ''
        for r in rows:
            if r.get('ten_vt'):
                ten_vt = r['ten_vt']
            if r.get('dvt'):
                dvt = r['dvt']
            if ten_vt and dvt:
                break

        # Build product data nếu có
        products = None
        if sp_codes:
            sp_list = [c.strip() for c in sp_codes.split(',') if c.strip()]
            if sp_list:
                # Lấy toàn bộ NXT sản phẩm của nguyên liệu này
                sp_sql = "SET NOCOUNT ON; EXEC sp_TonKho_NXT_TheoNVL @pMa_nvl=?"
                sp_rows = ds.query(sp_sql, [ma_vt])

                # Group by ma_vt, chỉ giữ các mã đang mở
                sp_map = {}
                for sr in sp_rows:
                    mk = sr.get('ma_vt', '')
                    if mk not in sp_list:
                        continue
                    if mk not in sp_map:
                        sp_map[mk] = {
                            'ma_vt': mk,
                            'ten_vt': sr.get('ten_vt', ''),
                            'dvt': sr.get('dvt', ''),
                            'ton': 0,
                            'rows': [],
                            '_latest_ym': 0,
                        }
                    sp_map[mk]['rows'].append(sr)
                    # Track tồn cuối kỳ mới nhất
                    ym = int(sr.get('nam', 0)) * 100 + int(sr.get('thang', 0))
                    if ym > sp_map[mk]['_latest_ym']:
                        sp_map[mk]['_latest_ym'] = ym
                        sp_map[mk]['ton'] = float(sr.get('CUOI_KI', 0) or 0)

                # Giữ thứ tự theo sp_list
                products = []
                for mk in sp_list:
                    if mk in sp_map:
                        p = sp_map[mk]
                        del p['_latest_ym']
                        products.append(p)

        from .excel_xuat import build_xuat_excel
        buf = build_xuat_excel(rows, ma_vt, ten_vt, dvt,
                               incl_xuatle=incl_xuatle, products=products)

        filename = f'Xuat_NVL_{ma_vt}.xlsx'
        return send_file(
            buf,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f'bcnl export-xuat error: {e}')
        return jsonify({'ok': False, 'error': str(e)}), 500