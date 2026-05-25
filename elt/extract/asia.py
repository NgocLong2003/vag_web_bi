"""
elt/extract/asia.py — Extract AsiaSoft ERP → Bronze Parquet
=============================================================
Connection: get_ds('source.asia') → pyodbc
Output:     get_ds('bronze.asia') → data/bronze/asia/{dim,fact}/

Usage:
    from elt.extract.asia import extract_asia
    results = extract_asia()                    # extract tất cả
    results = extract_asia(tables=['PTHUBAOCO']) # extract 1 bảng
"""

import logging
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from elt.connections import get_ds, get_config
from .base import (
    ExtractResult, Timer, clean_df, table_hash,
    detect_changes, has_changes, fmt_changes, fmt_dur,
    load_checksums, save_checksums, update_checksum,
    atomic_swap, ensure_dirs, read_parquet,
)

logger = logging.getLogger(__name__)

# Datasource names (đọc từ config.DATASOURCES)
SOURCE = 'source.asia'
TARGET = 'bronze.asia'


# ═══════════════════════════════════════════════════════
# VIEW REGISTRY
# ═══════════════════════════════════════════════════════

VIEW_REGISTRY = [
    # ── DIM ──
    {'name': 'DMNHANVIENKD', 'layer': 'dim', 'pk': 'ma_nvkd',
     'sql': 'SELECT ma_nvkd, ma_ql, ten_nvkd FROM DMNHANVIENKD_VIEW'},

    {'name': 'DMKHACHHANG', 'layer': 'dim', 'pk': 'ma_kh',
     'sql': """SELECT DISTINCT ma_kh, ten_kh, ma_bp, ma_nvkd,
                      ma_plkh1, ten_plkh1, ma_plkh2, ten_plkh2, ma_plkh3, ten_plkh3
               FROM DMKHACHHANG_VIEW
               WHERE ma_bp IS NOT NULL AND ma_bp != 'TN' AND ma_kh != 'TTT'
               UNION ALL
               SELECT 'TPBVSK','TPBVSK','TN','TPBVSK',
                      NULL,NULL,NULL,NULL,NULL,NULL"""},

    {'name': 'DMSANPHAM', 'layer': 'dim',
     'sql': 'SELECT * FROM DMSANPHAM_VIEW', 'optional': True},

    {'name': 'LOAISANPHAM', 'layer': 'dim',
     'sql': 'SELECT * FROM LOAISANPHAM_VIEW', 'optional': True},

    # ── FACT ──
    {'name': 'BKHDBANHANG', 'layer': 'fact',
     'sql': """SELECT ngay_ct, ma_kh, ma_vt, ten_vt, dvt, ma_bp, ma_nvkd, ma_kho,
                      so_luong, gia_nt2, tien_nt2, tien_ck_nt, ts_gtgt, thue_gtgt_nt
               FROM BKHDBANHANG_VIEW WHERE ma_bp != 'TN'"""},

    {'name': 'PTHUBAOCO', 'layer': 'fact',
     'sql': """SELECT ngay_ct, ma_ct, ma_kh_ct, ten_kh, dien_giai,
                      ma_bp, ma_nvkd, tk_co, tk_no, ps_co
               FROM PTHUBAOCO_VIEW WHERE tk_co = '131'"""},

    {'name': 'BANGKECHUNGTU', 'layer': 'fact',
     'sql': """SELECT ma_kh, tk, ma_ct, ngay_ct, ps_no, ps_co
               FROM BANGKECHUNGTU_VIEW WHERE tk = '131'"""},

    {'name': 'CONGNOKHDK', 'layer': 'fact',
     'sql': """SELECT ma_kh, nam, tk, du_no, du_co
               FROM CONGNOKHDK_VIEW WHERE tk = '131'"""},

    {'name': 'KY_BAO_CAO', 'layer': 'fact',
     'sql': 'SELECT * FROM ky_bao_cao'},

    {'name': 'THUONG', 'layer': 'fact',
     'sql': """SELECT ngay_ct, ma_kh_ct, ma_nvkd, dien_giai, thuong, ma_bp
               FROM THUONG_VIEW"""},

    {'name': 'TRALAI', 'layer': 'fact',
     'sql': """SELECT ngay_ct, ma_kh, ma_vt, ten_vt, dvt,
                      so_luong, gia_nt2, tien_nt2, tien_ck_nt,
                      thue_gtgt_nt, ma_bp, ma_nvkd
               FROM TRALAI_VIEW"""},
]


# ═══════════════════════════════════════════════════════
# BUSINESS TRANSFORMS
# ═══════════════════════════════════════════════════════

def _transform(name, table):
    import pyarrow.compute as pc

    if name == 'PTHUBAOCO':
        ma_kh = table.column('ma_kh_ct')
        ma_bp = table.column('ma_bp')
        new_bp = pc.if_else(pc.equal(ma_kh, 'XKCTWFC01'), 'XK', ma_bp)
        table = table.set_column(table.schema.get_field_index('ma_bp'), 'ma_bp', new_bp)
        try:
            ngay_ct = table.column('ngay_ct')
            ps_co = table.column('ps_co')
            is_gc = pc.equal(table.column('ma_kh_ct'), 'GCPHAVETCO')
            mask = pc.and_(is_gc, pc.and_(pc.equal(pc.year(ngay_ct), 2026), pc.equal(pc.month(ngay_ct), 2)))
            table = table.set_column(table.schema.get_field_index('ps_co'), 'ps_co',
                                     pc.if_else(mask, 0.0, pc.cast(ps_co, pa.float64())))
        except Exception:
            pass

    elif name == 'BKHDBANHANG':
        ma_nvkd = table.column('ma_nvkd')
        ma_bp = table.column('ma_bp')
        is_nvq02_vb = pc.and_(pc.equal(ma_nvkd, 'NVQ02'), pc.equal(ma_bp, 'VB'))
        new_nvkd = pc.if_else(is_nvq02_vb, 'NVQ03', ma_nvkd)
        table = table.set_column(table.schema.get_field_index('ma_nvkd'), 'ma_nvkd', new_nvkd)
        new_bp = pc.if_else(pc.equal(table.column('ma_nvkd'), 'NVQ03'), 'VB', ma_bp)
        table = table.set_column(table.schema.get_field_index('ma_bp'), 'ma_bp', new_bp)
        new_bp2 = pc.if_else(pc.equal(table.column('ma_kh'), 'XKCTWFC01'), 'XK', table.column('ma_bp'))
        table = table.set_column(table.schema.get_field_index('ma_bp'), 'ma_bp', new_bp2)

    return table


# ═══════════════════════════════════════════════════════
# PULL VIEW
# ═══════════════════════════════════════════════════════

def _pull_view(conn, sql):
    cur = conn.cursor()
    cur.execute(sql)
    columns = [col[0] for col in cur.description]
    rows = cur.fetchall()
    if not rows:
        return pa.table({col: pa.array([], type=pa.string()) for col in columns})
    col_data = {col: [] for col in columns}
    for row in rows:
        for i, col in enumerate(columns):
            col_data[col].append(row[i])
    return pa.table(col_data)


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def extract_asia(tables=None):
    """
    Extract AsiaSoft → Bronze Parquet.

    Args:
        tables: list tên bảng (None = tất cả)

    Returns:
        list[ExtractResult]
    """
    output_dir = Path(get_ds(TARGET))
    staging_dir = output_dir.parent / '_staging_asia'

    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    ensure_dirs(staging_dir / 'dim', staging_dir / 'fact', staging_dir / '_meta')

    checksums = load_checksums(output_dir / '_meta')
    results = []

    registry = VIEW_REGISTRY
    if tables:
        table_set = set(tables)
        registry = [v for v in VIEW_REGISTRY if v['name'] in table_set]

    print(f"\n[ASIA] Extract {len(registry)} views")
    logger.info(f"[Asia] Bắt đầu extract {len(registry)} views")

    try:
        conn = get_ds(SOURCE)
        conn.autocommit = True
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return [ExtractResult(table='_connection', status='error', error=str(e))]

    try:
        for vc in registry:
            name = vc['name']
            layer = vc['layer']
            pk = vc.get('pk')
            print(f"  {name}...", end=" ", flush=True)

            with Timer() as t:
                try:
                    table = _pull_view(conn, vc['sql'])
                    table = _transform(name, table)
                    pq.write_table(table, str(staging_dir / layer / f'{name}.parquet'), compression='snappy')

                    changes = None
                    if pk and layer == 'dim':
                        df_new = table.to_pandas()
                        df_old = read_parquet(output_dir / layer / f'{name}.parquet')
                        changes = detect_changes(df_new, df_old, pk)

                    df_hash = table.to_pandas()
                    changed = update_checksum(checksums, name, df_hash, changes)

                    results.append(ExtractResult(
                        table=name, layer=layer, rows=table.num_rows,
                        seconds=t.elapsed, changes=changes,
                        hash=checksums[name].get('hash'),
                    ))

                    extra = ""
                    if changes and has_changes(changes):
                        extra = f" ({fmt_changes(changes)})"
                    elif changed:
                        extra = " (changed)"
                    print(f"✓ {table.num_rows:,} dòng [{fmt_dur(t.elapsed)}]{extra}")

                except Exception as e:
                    is_optional = vc.get('optional', False)
                    results.append(ExtractResult(
                        table=name, layer=layer, seconds=t.elapsed,
                        status='error', error=str(e),
                        optional=is_optional,
                    ))
                    if is_optional:
                        print(f"✗ {e} [{fmt_dur(t.elapsed)}] (optional, skip)")
                    else:
                        print(f"✗ {e} [{fmt_dur(t.elapsed)}]")
                        conn.close()
                        shutil.rmtree(staging_dir, ignore_errors=True)
                        return results

        conn.close()
    except Exception as e:
        shutil.rmtree(staging_dir, ignore_errors=True)
        return [ExtractResult(table='_unexpected', status='error', error=str(e))]

    # Giữ file cũ cho bảng không extract lần này
    extracted = {r.table for r in results if r.status == 'ok'}
    if tables and output_dir.exists():
        for layer_name in ['dim', 'fact']:
            src = output_dir / layer_name
            dst = staging_dir / layer_name
            if src.exists():
                for f in src.glob('*.parquet'):
                    if f.stem not in extracted:
                        shutil.copy2(f, dst / f.name)

    save_checksums(staging_dir / '_meta', checksums)

    try:
        atomic_swap(staging_dir, output_dir)
    except Exception as e:
        results.append(ExtractResult(table='_swap', status='error', error=str(e)))

    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)

    return results