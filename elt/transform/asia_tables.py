"""
elt/transform/asia_tables.py — Copy bảng Asia bronze → silver (không merge)
=============================================================================
Các bảng đã chuyển sang merge transforms riêng:
  - PTHUBAOCO     → pthubaoco.py     (CNS doanh thu: PTT, CNT)
  - BKHDBANHANG   → bkhdbanhang.py   (CNS doanh số: HHA)
  - THUONG        → thuong.py        (CNS thưởng: PKK)
  - TRALAI        → tralai.py        (CNS trả lại: HBTL)
  - BANGKECHUNGTU → bangkechungtu.py (CNS công nợ: all mapped)
  - CONGNOKHDK    → congnokhdk.py    (CNS số dư đầu năm)
"""

from .base import CopyTransform, register

# ── DIM ──
register(CopyTransform('DMNHANVIENKD', layer='dim'))
register(CopyTransform('DMKHACHHANG',  layer='dim'))
register(CopyTransform('DMSANPHAM',    layer='dim'))
register(CopyTransform('LOAISANPHAM',  layer='dim'))

# ── FACT (chỉ copy, không merge CNS) ──
register(CopyTransform('KY_BAO_CAO',     layer='fact'))