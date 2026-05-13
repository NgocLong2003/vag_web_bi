"""
Sanfo Bronze — Query Test
===========================
Kiểm tra số liệu từ CongNoSoLuong Parquet.

Logic:
  Doanh thu  = SUM(PS_CO - PS_NO) WHERE MA_LOAI_CT IN ('PTT', 'CNT', 'PKK')
  Doanh số   = SUM(PS_NO - PS_CO) WHERE MA_LOAI_CT = 'HHA'
  Trả lại    = SUM(PS_CO - PS_NO) WHERE MA_LOAI_CT = 'HBTL'

Cách dùng:
    python sanfo_query_test.py
    python sanfo_query_test.py --path "Y:/code/vag_web_bi/data/bronze/sanfo/fact"
"""
import duckdb
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--path", default="data/bronze/sanfo/fact", help="Thư mục chứa Parquet")
args = parser.parse_args()

PQ = f"{args.path}/CongNoSoLuong.parquet"
con = duckdb.connect()

# ─── 1. Tổng hợp theo tháng ───
print("=" * 90)
print("TỔNG HỢP THEO THÁNG")
print("=" * 90)
rows = con.execute(f"""
    WITH base AS (
        SELECT
            YEAR(CAST(NGAY_CT AS DATE)) AS nam,
            MONTH(CAST(NGAY_CT AS DATE)) AS thang,
            MA_LOAI_CT, PS_NO, PS_CO
        FROM read_parquet('{PQ}')
    )
    SELECT
        nam, thang,
        SUM(CASE WHEN MA_LOAI_CT IN ('PTT','CNT','PKK') THEN PS_CO - PS_NO ELSE 0 END) AS doanh_thu,
        SUM(CASE WHEN MA_LOAI_CT = 'HHA' THEN PS_NO - PS_CO ELSE 0 END) AS doanh_so,
        SUM(CASE WHEN MA_LOAI_CT = 'HBTL' THEN PS_CO - PS_NO ELSE 0 END) AS tra_lai,
        COUNT(*) AS so_ct
    FROM base
    GROUP BY nam, thang
    ORDER BY nam, thang
""").fetchall()

print(f"  {'Tháng':<10} {'Doanh thu':>18} {'Doanh số':>18} {'Trả lại':>18} {'Số CT':>8}")
print(f"  {'─'*10} {'─'*18} {'─'*18} {'─'*18} {'─'*8}")
sum_dt = sum_ds = sum_tl = sum_ct = 0
for r in rows:
    print(f"  {r[0]}-{r[1]:02d}    {r[2]:>18,.0f} {r[3]:>18,.0f} {r[4]:>18,.0f} {r[5]:>8,}")
    sum_dt += r[2]; sum_ds += r[3]; sum_tl += r[4]; sum_ct += r[5]
print(f"  {'─'*10} {'─'*18} {'─'*18} {'─'*18} {'─'*8}")
print(f"  {'TỔNG':<10} {sum_dt:>18,.0f} {sum_ds:>18,.0f} {sum_tl:>18,.0f} {sum_ct:>8,}")


# ─── 2. Chi tiết T03/2026 ───
print()
print("=" * 90)
print("CHI TIẾT T03/2026")
print("=" * 90)

for label, loai_ct, formula in [
    ("Doanh thu (PTT+CNT+PKK)", "('PTT','CNT','PKK')", "PS_CO - PS_NO"),
    ("Doanh số (HHA)",          "('HHA')",              "PS_NO - PS_CO"),
    ("Trả lại (HBTL)",          "('HBTL')",             "PS_CO - PS_NO"),
]:
    result = con.execute(f"""
        SELECT
            SUM({formula}) AS gia_tri,
            SUM(PS_NO) AS tong_no,
            SUM(PS_CO) AS tong_co,
            COUNT(*) AS so_ct
        FROM read_parquet('{PQ}')
        WHERE MONTH(CAST(NGAY_CT AS DATE)) = 3
          AND YEAR(CAST(NGAY_CT AS DATE)) = 2026
          AND MA_LOAI_CT IN {loai_ct}
    """).fetchone()
    print(f"  {label}")
    print(f"    Giá trị:     {result[0]:>18,.0f}")
    print(f"    SUM(PS_NO):  {result[1]:>18,.0f}")
    print(f"    SUM(PS_CO):  {result[2]:>18,.0f}")
    print(f"    Số chứng từ: {result[3]:>18,}")
    print()


# ─── 3. Breakdown theo MA_LOAI_CT T03/2026 ───
print("=" * 90)
print("BREAKDOWN THEO LOẠI CHỨNG TỪ — T03/2026")
print("=" * 90)
rows2 = con.execute(f"""
    SELECT
        MA_LOAI_CT,
        TEN_LOAI_CT,
        COUNT(*) AS so_ct,
        SUM(PS_NO) AS tong_no,
        SUM(PS_CO) AS tong_co,
        SUM(PS_NO - PS_CO) AS no_tru_co,
        SUM(PS_CO - PS_NO) AS co_tru_no
    FROM read_parquet('{PQ}')
    WHERE MONTH(CAST(NGAY_CT AS DATE)) = 3
      AND YEAR(CAST(NGAY_CT AS DATE)) = 2026
    GROUP BY MA_LOAI_CT, TEN_LOAI_CT
    ORDER BY SUM(PS_NO) + SUM(PS_CO) DESC
""").fetchall()
print(f"  {'Mã':<8} {'Tên':<32} {'Số CT':>7} {'PS_NO':>16} {'PS_CO':>16} {'NO-CO':>16} {'CO-NO':>16}")
print(f"  {'─'*8} {'─'*32} {'─'*7} {'─'*16} {'─'*16} {'─'*16} {'─'*16}")
for r in rows2:
    print(f"  {r[0]:<8} {(r[1] or '')[:32]:<32} {r[2]:>7,} {r[3]:>16,.0f} {r[4]:>16,.0f} {r[5]:>16,.0f} {r[6]:>16,.0f}")


# ─── 4. Top 10 đối tượng doanh thu T03/2026 ───
print()
print("=" * 90)
print("TOP 10 ĐỐI TƯỢNG DOANH THU T03/2026 (PTT+CNT+PKK)")
print("=" * 90)
rows3 = con.execute(f"""
    SELECT
        MA_DT, TEN_DT,
        SUM(PS_CO - PS_NO) AS doanh_thu,
        COUNT(*) AS so_ct
    FROM read_parquet('{PQ}')
    WHERE MONTH(CAST(NGAY_CT AS DATE)) = 3
      AND YEAR(CAST(NGAY_CT AS DATE)) = 2026
      AND MA_LOAI_CT IN ('PTT', 'CNT', 'PKK')
    GROUP BY MA_DT, TEN_DT
    ORDER BY doanh_thu DESC
    LIMIT 10
""").fetchall()
print(f"  {'Mã ĐT':<16} {'Tên':<32} {'Doanh thu':>16} {'Số CT':>7}")
print(f"  {'─'*16} {'─'*32} {'─'*16} {'─'*7}")
for r in rows3:
    print(f"  {(r[0] or ''):<16} {(r[1] or '')[:32]:<32} {r[2]:>16,.0f} {r[3]:>7,}")

con.close()
print("\n✓ Done")