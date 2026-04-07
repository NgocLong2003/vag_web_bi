"""
dim_history.py — SCD Type 2: Ghi lịch sử biến động DMNVKD & DMKH

Mỗi lần sync:
  - SELECT * từ VIEW nguồn
  - Tính hash các cột quan trọng → so sánh với bản current (valid_to IS NULL)
  - Mới     → INSERT (valid_from = ldate/ngay_sua hoặc today)
  - Thay đổi → close bản cũ + INSERT bản mới
  - Bị xóa  → close bản cũ
  - Không đổi → bỏ qua

Usage:
    from dim_history import sync_dim_history
    sync_dim_history(sqlserver_config)
"""

import hashlib
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)


def _hash_row(vals):
    raw = '|'.join(str(v or '') for v in vals)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _get_conn(config):
    import pyodbc
    c = config
    return pyodbc.connect(
        f"DRIVER={{{c['driver']}}};SERVER={c['server']},{c['port']};"
        f"DATABASE={c['database']};UID={c['username']};PWD={c['password']};"
        "TrustServerCertificate=yes;Connect Timeout=30;",
        autocommit=False
    )


def _to_date(val):
    """Convert datetime/smalldatetime/string → date, hoặc None."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        return datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
    except:
        return None


# ═══════════════════════════════════════════════════════════
# Cấu hình 2 dimensions
# ═══════════════════════════════════════════════════════════

DIM_CONFIGS = [
    {
        'name': 'NHANVIEN',
        'source_sql': "SELECT * FROM DMNHANVIENKD_VIEW WHERE ma_nvkd IS NOT NULL AND ma_nvkd != ''",
        'history_table': 'dim_nhanvien_history',
        'key_col': 'ma_nvkd',
        # Cột dùng để tính hash (detect thay đổi) — chỉ cần các cột nghiệp vụ quan trọng
        'hash_cols': ['ten_nvkd', 'ma_ql', 'ma_ql1', 'ksd', 'stt_nhom', 'cap'],
        # Cột chứa ngày sửa cuối → dùng làm valid_from
        'date_col': 'ldate',
        # Fallback: ngày tạo nếu chưa sửa
        'fallback_date_col': 'cdate',
        # Tất cả cột insert (khớp với bảng history, KHÔNG bao gồm SCD fields)
        'insert_cols': ['ma_cty', 'ma_nvkd', 'ten_nvkd', 'ksd', 'cdate', 'cuser',
                        'ldate', 'luser', 'ma_ql', 'stt_nhom', 'cap', 'ma_ql1'],
    },
    {
        'name': 'KHACHHANG',
        'source_sql': """SELECT * FROM DMKHACHHANG_VIEW
                         WHERE ma_kh IS NOT NULL AND ma_kh != '' AND ma_bp != 'TN'""",
        'history_table': 'dim_khachhang_history',
        'key_col': 'ma_kh',
        'hash_cols': ['ten_kh', 'ma_nvkd', 'ma_bp', 'dia_chi', 'ma_so_thue',
                      'ma_nhkh', 'ma_plkh1', 'ma_plkh2', 'ma_plkh3', 'ksd'],
        'date_col': 'ngay_sua',
        'fallback_date_col': 'ngay_tao',
        'insert_cols': ['ma_kh', 'ten_kh', 'dia_chi', 'ma_so_thue', 'iskh', 'isNCC',
                        'isNSX', 'isNV', 'ma_nhkh', 'ten_nhkh', 'ma_plkh1', 'ten_plkh1',
                        'ma_plkh2', 'ten_plkh2', 'ma_plkh3', 'ten_plkh3', 'ma_bp', 'ten_bp',
                        'ma_nvkd', 'ten_nvkd', 'quoc_gia', 'nguoi_tao', 'ngay_tao',
                        'nguoi_sua', 'ngay_sua', 'ksd'],
    },
]


def _sync_one_dim(conn, cfg):
    """Sync 1 dimension table theo SCD Type 2."""
    cur = conn.cursor()
    today = date.today()
    table = cfg['history_table']
    key_col = cfg['key_col']

    # 1. Lấy data nguồn
    cur.execute(cfg['source_sql'])
    src_cols = [d[0] for d in cur.description]
    src_rows = cur.fetchall()

    src_map = {}
    for row in src_rows:
        rd = {src_cols[i]: row[i] for i in range(len(src_cols))}
        key = str(rd.get(key_col) or '').strip()
        if not key:
            continue
        hash_vals = [rd.get(c) for c in cfg['hash_cols']]
        rd['_hash'] = _hash_row(hash_vals)
        # valid_from = ngày sửa cuối → ngày tạo → 1990-01-01
        date_col = cfg['date_col']
        fallback_col = cfg['fallback_date_col']
        vf = _to_date(rd.get(date_col)) or _to_date(rd.get(fallback_col)) or date(1990, 1, 1)
        rd['_valid_from'] = vf
        src_map[key] = rd

    # 2. Lấy bản current từ history
    cur.execute(f'SELECT {key_col}, snapshot_hash FROM {table} WHERE valid_to IS NULL')
    cur_map = {}
    for row in cur.fetchall():
        k = str(row[0] or '').strip()
        if k:
            cur_map[k] = row[1]

    # 3. Diff
    new_keys = set(src_map.keys()) - set(cur_map.keys())
    del_keys = set(cur_map.keys()) - set(src_map.keys())
    common_keys = set(src_map.keys()) & set(cur_map.keys())
    changed_keys = {k for k in common_keys if src_map[k]['_hash'] != cur_map[k]}

    n_new, n_del, n_chg = len(new_keys), len(del_keys), len(changed_keys)

    if n_new == 0 and n_del == 0 and n_chg == 0:
        logger.info(f"  [{cfg['name']}] Không thay đổi ({len(src_map)} records)")
        return

    # 4. Close deleted + changed
    close_keys = del_keys | changed_keys
    if close_keys:
        for k in close_keys:
            cur.execute(
                f'UPDATE {table} SET valid_to = ? WHERE {key_col} = ? AND valid_to IS NULL',
                (today, k)
            )

    # 5. Insert new + changed
    insert_keys = new_keys | changed_keys
    if insert_keys:
        all_cols = cfg['insert_cols'] + ['valid_from', 'snapshot_hash']
        placeholders = ','.join(['?'] * len(all_cols))
        col_names = ','.join(all_cols)
        insert_sql = f'INSERT INTO {table} ({col_names}) VALUES ({placeholders})'

        for k in insert_keys:
            rd = src_map[k]
            vals = [rd.get(c) for c in cfg['insert_cols']]
            vals.append(rd['_valid_from'])
            vals.append(rd['_hash'])
            cur.execute(insert_sql, vals)

    conn.commit()
    logger.info(
        f"  [{cfg['name']}] +{n_new} mới, ~{n_chg} thay đổi, -{n_del} xóa "
        f"(tổng {len(src_map)})"
    )


def sync_dim_history(sqlserver_config):
    """Sync lịch sử biến động cho tất cả dimensions."""
    try:
        conn = _get_conn(sqlserver_config)
        for cfg in DIM_CONFIGS:
            try:
                _sync_one_dim(conn, cfg)
            except Exception as e:
                logger.error(f"  [{cfg['name']}] Lỗi: {e}")
                # Rollback lỗi từng dim, không ảnh hưởng dim khác
                try:
                    conn.rollback()
                except:
                    pass
        conn.close()
        logger.info("[DimHistory] ✓ Hoàn thành")
    except Exception as e:
        logger.error(f"[DimHistory] ✗ Connection error: {e}")