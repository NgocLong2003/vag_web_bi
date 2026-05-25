"""
elt/gold/tpbvsk.py — Gold: doanh thu + doanh số TPBVSK theo tháng
===================================================================
Đọc từ silver (PTHUBAOCO, BKHDBANHANG) → aggregate theo tháng
→ UNION với seed 2024 (manual) → ghi gold Delta Lake.

Output:
  gold/input_doanh_thu_tpbvsk  (year_admin, month_admin, ma_kh, ma_bp, nguoi_gd, doanhthu, ma_nvkd)
  gold/input_doanh_so_tpbvsk   (year_admin, month_admin, ma_kh, ma_bp, ma_nvkd, doanhso, ten_nvkd, ngay_admin)
"""

import logging
import os
import time as _time
from pathlib import Path

import pandas as pd

from elt.connections import get_ds

logger = logging.getLogger(__name__)

SEED_DIR = Path('data/seed')


def _gold_path(table_name):
    """Absolute path đến gold Delta table."""
    return os.path.abspath(os.path.join(get_ds('gold'), table_name))


def _read_silver_parquet(table_name):
    """Đọc silver table qua DuckDB (tái dụng Delta reader)."""
    from elt.transform.base import read_bronze
    # Silver = delta lake, đọc trực tiếp file parquet qua deltalake
    from deltalake import DeltaTable
    silver_dir = os.path.abspath(get_ds('silver'))
    table_path = os.path.join(silver_dir, table_name)
    try:
        dt = DeltaTable(table_path)
        return dt.to_pandas()
    except Exception as e:
        logger.error(f"[Gold] Cannot read silver/{table_name}: {e}")
        return None


def _write_gold(table_name, df):
    """Ghi DataFrame vào gold Delta Lake."""
    from deltalake import write_deltalake, DeltaTable
    import pyarrow as pa

    out = _gold_path(table_name)
    pa_table = pa.Table.from_pandas(df, preserve_index=False)

    if len(pa_table) == 0:
        logger.warning(f"[Gold] {table_name}: empty, skipping")
        return -1

    write_deltalake(out, pa_table, mode='overwrite')
    dt = DeltaTable(out)
    return dt.version()


def build_doanh_thu_tpbvsk():
    """
    Gold: doanh thu TPBVSK theo tháng.
    Source: silver/PTHUBAOCO WHERE ma_kh_ct='TPBVSK' AND tk_co='131'
            + MA_LOAI_CT IN (PTT, CNT) đã filter ở silver transform
    """
    t0 = _time.time()

    # 1. Đọc silver PTHUBAOCO
    df = _read_silver_parquet('PTHUBAOCO')
    if df is None:
        return {'table': 'input_doanh_thu_tpbvsk', 'status': 'error', 'error': 'PTHUBAOCO not found'}

    # Filter TPBVSK + tk_co=131
    mask = (df['ma_kh_ct'] == 'TPBVSK') & (df['tk_co'] == '131')
    df = df[mask].copy()

    if not df.empty:
        df['ngay_ct'] = pd.to_datetime(df['ngay_ct'])
        df['year_admin'] = df['ngay_ct'].dt.year
        df['month_admin'] = df['ngay_ct'].dt.month
        df['ps_co'] = pd.to_numeric(df['ps_co'], errors='coerce').fillna(0)

        agg = df.groupby(['year_admin', 'month_admin'], as_index=False).agg(
            doanhthu=('ps_co', 'sum')
        )
        agg['ma_kh'] = 'TPBVSK'
        agg['ma_bp'] = 'TN'
        agg['nguoi_gd'] = 'TPBVSK'
        agg['ma_nvkd'] = 'TPBVSK'
    else:
        agg = pd.DataFrame(columns=['year_admin', 'month_admin', 'doanhthu',
                                     'ma_kh', 'ma_bp', 'nguoi_gd', 'ma_nvkd'])

    # 2. Đọc seed 2024
    seed_path = SEED_DIR / 'input_doanh_thu_tpbvsk_2024.csv'
    if seed_path.exists():
        seed = pd.read_csv(seed_path)
        # Bỏ năm đã có trong silver (tránh duplicate)
        silver_years = set(agg['year_admin'].unique()) if not agg.empty else set()
        seed = seed[~seed['year_admin'].isin(silver_years)]
    else:
        seed = pd.DataFrame()

    # 3. UNION
    cols = ['year_admin', 'month_admin', 'ma_kh', 'ma_bp', 'nguoi_gd', 'doanhthu', 'ma_nvkd']
    if not seed.empty:
        result = pd.concat([seed[cols], agg[cols]], ignore_index=True)
    else:
        result = agg[cols]

    result = result.sort_values(['year_admin', 'month_admin']).reset_index(drop=True)

    # 4. Ghi gold
    version = _write_gold('input_doanh_thu_tpbvsk', result)
    elapsed = round(_time.time() - t0, 2)

    logger.info(f"[Gold] input_doanh_thu_tpbvsk: {len(result)} rows, {elapsed}s (v{version})")
    return {'table': 'input_doanh_thu_tpbvsk', 'status': 'ok',
            'rows': len(result), 'seconds': elapsed, 'version': version}


def build_doanh_so_tpbvsk():
    """
    Gold: doanh số TPBVSK theo tháng.
    Source: silver/BKHDBANHANG WHERE ma_kh='TPBVSK'
    """
    t0 = _time.time()

    # 1. Đọc silver BKHDBANHANG
    df = _read_silver_parquet('BKHDBANHANG')
    if df is None:
        return {'table': 'input_doanh_so_tpbvsk', 'status': 'error', 'error': 'BKHDBANHANG not found'}

    # Filter TPBVSK
    df = df[df['ma_kh'] == 'TPBVSK'].copy()

    if not df.empty:
        df['ngay_ct'] = pd.to_datetime(df['ngay_ct'])
        df['year_admin'] = df['ngay_ct'].dt.year
        df['month_admin'] = df['ngay_ct'].dt.month
        df['tien_nt2'] = pd.to_numeric(df['tien_nt2'], errors='coerce').fillna(0)

        agg = df.groupby(['year_admin', 'month_admin'], as_index=False).agg(
            doanhso=('tien_nt2', 'sum')
        )
        agg['ma_kh'] = 'TPBVSK'
        agg['ma_bp'] = 'TN'
        agg['ma_nvkd'] = 'TPBVSK'
        agg['ten_nvkd'] = 'TPBVSK'
        agg['ngay_admin'] = pd.to_datetime(
            agg['year_admin'].astype(str) + '-' + agg['month_admin'].astype(str).str.zfill(2) + '-01'
        )
    else:
        agg = pd.DataFrame(columns=['year_admin', 'month_admin', 'doanhso',
                                     'ma_kh', 'ma_bp', 'ma_nvkd', 'ten_nvkd', 'ngay_admin'])

    # 2. Đọc seed 2024
    seed_path = SEED_DIR / 'input_doanh_so_tpbvsk_2024.csv'
    if seed_path.exists():
        seed = pd.read_csv(seed_path)
        seed['ngay_admin'] = pd.to_datetime(seed['ngay_admin'])
        silver_years = set(agg['year_admin'].unique()) if not agg.empty else set()
        seed = seed[~seed['year_admin'].isin(silver_years)]
    else:
        seed = pd.DataFrame()

    # 3. UNION
    cols = ['year_admin', 'month_admin', 'ma_kh', 'ma_bp', 'ma_nvkd', 'doanhso', 'ten_nvkd', 'ngay_admin']
    if not seed.empty:
        result = pd.concat([seed[cols], agg[cols]], ignore_index=True)
    else:
        result = agg[cols]

    result = result.sort_values(['year_admin', 'month_admin']).reset_index(drop=True)

    # 4. Ghi gold
    version = _write_gold('input_doanh_so_tpbvsk', result)
    elapsed = round(_time.time() - t0, 2)

    logger.info(f"[Gold] input_doanh_so_tpbvsk: {len(result)} rows, {elapsed}s (v{version})")
    return {'table': 'input_doanh_so_tpbvsk', 'status': 'ok',
            'rows': len(result), 'seconds': elapsed, 'version': version}


def run_gold_tpbvsk():
    """Chạy cả 2 gold tables, push lên SQL Server."""
    results = []
    results.append(build_doanh_thu_tpbvsk())
    results.append(build_doanh_so_tpbvsk())

    ok = sum(1 for r in results if r.get('status') == 'ok')
    print(f"[GOLD] TPBVSK: {ok}/{len(results)} OK")
    for r in results:
        status = '✓' if r.get('status') == 'ok' else '✗'
        print(f"  {r['table']}... {status} {r.get('rows', 0):,} dòng [{r.get('seconds', 0)}s]")

    # Push lên SQL Server
    if ok > 0:
        try:
            _push_to_sqlserver()
        except Exception as e:
            logger.error(f"[Gold] SQL Server push failed: {e}")
            print(f"  ✗ SQL Server push: {e}")

    return results


def _push_to_sqlserver():
    """Push gold tables lên SQL Server (source.asia) để Power BI đọc."""
    from elt.connections import get_ds

    conn = get_ds('source.asia')
    conn.autocommit = True
    cursor = conn.cursor()

    # ── Doanh thu ──
    dt = _read_gold('input_doanh_thu_tpbvsk')
    if dt is not None and not dt.empty:
        _upsert_table(cursor, 'input_doanh_thu_tpbvsk', dt, [
            ('year_admin', 'INT'),
            ('month_admin', 'INT'),
            ('ma_kh', 'NVARCHAR(50)'),
            ('ma_bp', 'NVARCHAR(50)'),
            ('nguoi_gd', 'NVARCHAR(50)'),
            ('doanhthu', 'DECIMAL(18,0)'),
            ('ma_nvkd', 'NVARCHAR(50)'),
        ])
        print(f"  ✓ SQL Server: input_doanh_thu_tpbvsk ({len(dt)} rows)")

    # ── Doanh số ──
    ds = _read_gold('input_doanh_so_tpbvsk')
    if ds is not None and not ds.empty:
        _upsert_table(cursor, 'input_doanh_so_tpbvsk', ds, [
            ('year_admin', 'INT'),
            ('month_admin', 'INT'),
            ('ma_kh', 'NVARCHAR(50)'),
            ('ma_bp', 'NVARCHAR(50)'),
            ('ma_nvkd', 'NVARCHAR(50)'),
            ('doanhso', 'DECIMAL(18,0)'),
            ('ten_nvkd', 'NVARCHAR(100)'),
            ('ngay_admin', 'DATE'),
        ])
        print(f"  ✓ SQL Server: input_doanh_so_tpbvsk ({len(ds)} rows)")

    cursor.close()
    conn.close()


def _read_gold(table_name):
    """Đọc gold Delta table."""
    from deltalake import DeltaTable
    try:
        dt = DeltaTable(_gold_path(table_name))
        return dt.to_pandas()
    except:
        return None


def _upsert_table(cursor, table_name, df, schema):
    """
    Truncate + insert vào SQL Server.
    Tạo bảng nếu chưa có.
    """
    # Tạo bảng nếu chưa có
    cols_ddl = ', '.join(f'[{name}] {dtype}' for name, dtype in schema)
    cursor.execute(f"""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{table_name}')
        CREATE TABLE [dbo].[{table_name}] ({cols_ddl})
    """)

    # Truncate
    cursor.execute(f"TRUNCATE TABLE [dbo].[{table_name}]")

    # Insert
    col_names = [s[0] for s in schema]
    placeholders = ', '.join(['?'] * len(col_names))
    insert_sql = f"INSERT INTO [dbo].[{table_name}] ([{'],['.join(col_names)}]) VALUES ({placeholders})"

    for _, row in df.iterrows():
        values = []
        for col in col_names:
            v = row.get(col)
            if pd.isna(v):
                values.append(None)
            else:
                values.append(v)
        cursor.execute(insert_sql, values)

    logger.info(f"[Gold→SQL] {table_name}: {len(df)} rows pushed")