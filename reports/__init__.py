"""
VietAnh BI — Reports Registry
Mỗi báo cáo tự viết = 1 entry ở đây.

Cách thêm báo cáo mới:
1. Tạo folder reports/ten_baocao/ với __init__.py chứa Blueprint
2. Thêm entry vào REPORT_REGISTRY bên dưới
3. Trong admin, tạo dashboard với dashboard_type='report', slug khớp với slug ở đây
4. Phân quyền như dashboard bình thường
"""

# Registry: slug → { blueprint, template }
# blueprint sẽ được mount vào app với url_prefix /reports/<slug>
# template là tên file html trong folder templates/ của báo cáo đó

REPORT_REGISTRY = {}


def register_report(slug, blueprint, template):
    """Đăng ký 1 báo cáo vào registry"""
    REPORT_REGISTRY[slug] = {
        'blueprint': blueprint,
        'template': template,
    }


def get_report(slug):
    """Lấy thông tin báo cáo theo slug"""
    return REPORT_REGISTRY.get(slug)


def get_all_blueprints():
    """Trả về list tất cả blueprints để app.py register"""
    return [(slug, info['blueprint']) for slug, info in REPORT_REGISTRY.items()]


# ==============================================================
# ĐĂNG KÝ CÁC BÁO CÁO Ở ĐÂY
# ==============================================================

# Báo cáo Kinh Doanh
from reports.baocao_kinhdoanh import bp as bckd_bp
register_report('bao-cao-kinh-doanh', bckd_bp, 'baocao_kinhdoanh/baocao_kd.html')

# Báo cáo Khách Hàng
from reports.baocao_khachhang import bp as bckh_bp
register_report('bao-cao-khach-hang', bckh_bp, 'baocao_khachhang/baocao_kh.html')

# Báo cáo Chi Tiết
from reports.baocao_chitiet import bp as bcct_bp
register_report('bao-cao-chi-tiet', bcct_bp, 'baocao_chitiet/baocao_ct.html')

from reports.bao_cao_ban_ra import bp as bcbr_bp
register_report('bao-cao-ban-ra', bcbr_bp, 'baocao_banra/baocao_banra.html')

# Thêm báo cáo mới:
# from reports.baocao_tonkho import bp as bctonkho_bp
# register_report('ton-kho', bctonkho_bp, 'baocao_tonkho/tonkho.html')