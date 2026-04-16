"""
VietAnh BI — Reports Registry

Cách thêm báo cáo mới:
1. Tạo folder reports/ten_baocao/ với __init__.py chứa Blueprint
2. Thêm entry register_report() bên dưới
3. Trong admin, tạo dashboard với dashboard_type='report', slug khớp
4. Phân quyền như dashboard bình thường

Datasource:
  'default'    → DuckDB (Parquet batch, delay 30 phút)
  'production' → SQL Server trực tiếp (realtime)
"""

REPORT_REGISTRY = {}


def register_report(slug, blueprint, template, datasource='default', category=''):
    """Đăng ký 1 báo cáo vào registry.

    Args:
        slug: URL slug (khớp với dashboards.slug)
        blueprint: Flask Blueprint
        template: template path
        datasource: tên datasource ('default', 'production', ...)
        category: phân loại nghiệp vụ ('Kinh doanh', 'Sản xuất', ...)
    """
    REPORT_REGISTRY[slug] = {
        'blueprint': blueprint,
        'template': template,
        'datasource': datasource,
        'category': category,
    }


def get_report(slug):
    return REPORT_REGISTRY.get(slug)


def get_all_blueprints():
    return [(slug, info['blueprint']) for slug, info in REPORT_REGISTRY.items()]


# ==============================================================
# KINH DOANH (DuckDB batch)
# ==============================================================

from reports.baocao_kinhdoanh import bp as bckd_bp
register_report('bao-cao-kinh-doanh', bckd_bp, 'baocao_kinhdoanh/baocao_kd.html',
                datasource='default', category='Kinh doanh')

from reports.baocao_khachhang import bp as bckh_bp
register_report('bao-cao-khach-hang', bckh_bp, 'baocao_khachhang/baocao_kh.html',
                datasource='default', category='Kinh doanh')

from reports.baocao_chitiet import bp as bcct_bp
register_report('bao-cao-chi-tiet', bcct_bp, 'baocao_chitiet/baocao_ct.html',
                datasource='default', category='Kinh doanh')

# ==============================================================
# KẾ TOÁN (DuckDB batch)
# ==============================================================

from reports.bao_cao_ban_ra import bp as bcbr_bp
register_report('bao-cao-ban-ra', bcbr_bp, 'baocao_banra/baocao_banra.html',
                datasource='default', category='Kế toán')

# ==============================================================
# QUẢN TRỊ (DuckDB + SQL Server hybrid)
# ==============================================================

from reports.baocao_kpi import bp as bckpi_bp
register_report('bao-cao-kpi', bckpi_bp, 'baocao_kpi/baocao_kpi.html',
                datasource='default', category='Quản trị')

# ==============================================================
# SẢN XUẤT (SQL Server realtime)
# ==============================================================

from reports.san_xuat.baocao_nguyenlieu import bp as bcnl_bp
register_report('bao-cao-nguyen-lieu', bcnl_bp, 'san_xuat/baocao_nguyenlieu/baocao_nguyenlieu.html',
                datasource='sanxuat', category='Sản xuất')

from reports.san_xuat.canhbao_tonkho import bp as cbtk_bp
register_report('canh-bao-ton-kho', cbtk_bp,
                'san_xuat/canhbao_tonkho/canhbao_tonkho.html',
                datasource='sanxuat', category='Sản xuất')