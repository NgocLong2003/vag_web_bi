"""
data_sync.py — ETL: SQL Server → Parquet (atomic swap)

Scheduler chạy mỗi 30 phút:
  1. Kết nối SQL Server, pull từng view → DataFrame
  2. Ghi vào data/staging/*.parquet
  3. Atomic swap: rename staging → current
  4. Nếu lỗi bất kỳ bước nào → bỏ qua lượt, giữ nguyên data cũ

Usage:
    from data_sync import DataSync
    sync = DataSync(sqlserver_config)
    sync.start()          # chạy background thread, 30 phút/lần
    sync.run_once()       # chạy 1 lần (blocking)
    sync.stop()           # dừng scheduler
"""

import os
import shutil
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

import pyodbc
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# Registry: tất cả views cần sync
# Thêm view mới → thêm 1 dòng vào đây
# ─────────────────────────────────────────
VIEW_REGISTRY = [
    {
        'name': 'DMNHANVIENKD',
        'sql': 'SELECT ma_nvkd, ma_ql, ten_nvkd FROM DMNHANVIENKD_VIEW',
    },
    {
        'name': 'DMKHACHHANG',
        'sql': """SELECT DISTINCT ma_kh, ten_kh, ma_bp, ma_nvkd, ma_plkh1, ten_plkh1, ma_plkh2, ten_plkh2, ma_plkh3, ten_plkh3
                  FROM DMKHACHHANG_VIEW
                  WHERE ma_bp IS NOT NULL AND ma_bp != 'TN' AND ma_kh != 'TTT'""",
    },
    {
        'name': 'BANGKECHUNGTU',
        'sql': """SELECT ma_kh, tk, ma_ct, ngay_ct, ps_no, ps_co
                  FROM BANGKECHUNGTU_VIEW
                  WHERE tk = '131'""",
    },
    {
        'name': 'BKHDBANHANG',
        'sql': """SELECT ngay_ct, ma_kh, ma_vt, ten_vt, dvt, ma_bp, ma_nvkd, ma_kho,
                         so_luong, gia_nt2, tien_nt2, tien_ck_nt, ts_gtgt,
                         thue_gtgt_nt
                  FROM BKHDBANHANG_VIEW
                  WHERE ma_bp != 'TN'""",
    },
    {
        'name': 'PTHUBAOCO',
        'sql': """SELECT ngay_ct, ma_ct, ma_kh_ct, ten_kh, dien_giai,
                         ma_bp, ma_nvkd, tk_co, tk_no, ps_co
                  FROM PTHUBAOCO_VIEW
                  WHERE tk_co = '131'""",
    },
    {
        'name': 'CONGNOKHDK',
        'sql': """SELECT ma_kh, nam, tk, du_no, du_co
                  FROM CONGNOKHDK_VIEW
                  WHERE tk = '131'""",
    },
    {
        'name': 'KY_BAO_CAO',
        'sql': 'SELECT * FROM ky_bao_cao',
    },
    {
        'name': 'THUONG',
        'sql': """SELECT ngay_ct, ma_kh_ct, ma_nvkd, dien_giai, thuong
                  FROM THUONG_VIEW""",
    },
    {
        'name': 'TRALAI',
        'sql': """SELECT ngay_ct, ma_kh, ma_vt, ten_vt, dvt,
                         so_luong, gia_nt2, tien_nt2, tien_ck_nt,
                         thue_gtgt_nt
                  FROM TRALAI_VIEW""",
    },
    {
        'name': 'DMSANPHAM',
        'sql': 'SELECT * FROM DMSANPHAM_VIEW',

    },
    {
        'name': 'LOAISANPHAM',
        'sql': 'SELECT * FROM LOAISANPHAM_VIEW',    
    }
]


class DataSync:
    def __init__(self, sqlserver_config, data_dir='data', interval=1800, on_success=None):
        """
        Args:
            sqlserver_config: dict với keys: driver, server, port, database, username, password
            data_dir: thư mục gốc chứa data (mặc định: 'data')
            interval: giây giữa các lần sync (mặc định: 1800 = 30 phút)
            on_success: callback gọi sau mỗi sync thành công (optional)
        """
        self.config = sqlserver_config
        self.data_dir = Path(data_dir)
        self.current_dir = self.data_dir / 'current'
        self.staging_dir = self.data_dir / 'staging'
        self.interval = interval
        self.on_success = on_success
        self._thread = None
        self._stop_event = threading.Event()
        self.last_sync = None
        self.last_error = None
        self.sync_count = 0

        # Tạo thư mục
        self.current_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        c = self.config
        return pyodbc.connect(
            f"DRIVER={{{c['driver']}}};SERVER={c['server']},{c['port']};"
            f"DATABASE={c['database']};UID={c['username']};PWD={c['password']};"
            "TrustServerCertificate=yes;Connect Timeout=30;",
            timeout=30
        )

    def _pull_view(self, conn, view_config):
        """Pull 1 view → pyarrow Table"""
        cur = conn.cursor()
        cur.execute(view_config['sql'])
        columns = [col[0] for col in cur.description]
        rows = cur.fetchall()
        # Convert to columnar format
        if not rows:
            return pa.table({col: pa.array([], type=pa.string()) for col in columns})
        col_data = {col: [] for col in columns}
        for row in rows:
            for i, col in enumerate(columns):
                val = row[i]
                col_data[col].append(val)
        return pa.table(col_data)

    def _transform(self, name, table):
        """Áp dụng business transforms sau khi pull, trước khi ghi parquet.
        Matching Power Query logic."""
        import pyarrow.compute as pc

        if name == 'PTHUBAOCO':
            # 1. XKCTWFC01 → ma_bp = 'XK'
            ma_kh = table.column('ma_kh_ct')
            ma_bp = table.column('ma_bp')
            new_bp = pc.if_else(pc.equal(ma_kh, 'XKCTWFC01'), 'XK', ma_bp)
            table = table.set_column(table.schema.get_field_index('ma_bp'), 'ma_bp', new_bp)

            # 2. GCPHAVETCO + Feb 2026 → ps_co = 0
            ngay_ct = table.column('ngay_ct')
            ps_co = table.column('ps_co')
            # Build mask: ma_kh='GCPHAVETCO' AND year=2026 AND month=2
            is_gc = pc.equal(table.column('ma_kh_ct'), 'GCPHAVETCO')
            # ngay_ct might be date or datetime
            try:
                yr = pc.year(ngay_ct)
                mn = pc.month(ngay_ct)
                is_feb26 = pc.and_(pc.equal(yr, 2026), pc.equal(mn, 2))
                mask = pc.and_(is_gc, is_feb26)
                new_ps = pc.if_else(mask, 0.0, pc.cast(ps_co, pa.float64()))
                table = table.set_column(table.schema.get_field_index('ps_co'), 'ps_co', new_ps)
            except:
                pass  # If ngay_ct is string, skip this transform

            logger.info(f"    [Transform] PTHUBAOCO: XKCTWFC01→XK, GCPHAVETCO zero")

        elif name == 'BKHDBANHANG':
            # 1. NVQ02 + ma_bp=VB → ma_nvkd = NVQ03
            ma_nvkd = table.column('ma_nvkd')
            ma_bp = table.column('ma_bp')
            is_nvq02_vb = pc.and_(pc.equal(ma_nvkd, 'NVQ02'), pc.equal(ma_bp, 'VB'))
            new_nvkd = pc.if_else(is_nvq02_vb, 'NVQ03', ma_nvkd)
            table = table.set_column(table.schema.get_field_index('ma_nvkd'), 'ma_nvkd', new_nvkd)

            # 2. NVQ03 → ma_bp = VB (covers both original NVQ03 and transformed NVQ02)
            new_nvkd2 = table.column('ma_nvkd')
            new_bp = pc.if_else(pc.equal(new_nvkd2, 'NVQ03'), 'VB', ma_bp)
            table = table.set_column(table.schema.get_field_index('ma_bp'), 'ma_bp', new_bp)

            # 3. ma_kh = XKCTWFC01 → ma_bp = XK
            ma_kh = table.column('ma_kh')
            new_bp2 = pc.if_else(pc.equal(ma_kh, 'XKCTWFC01'), 'XK', table.column('ma_bp'))
            table = table.set_column(table.schema.get_field_index('ma_bp'), 'ma_bp', new_bp2)

            logger.info(f"    [Transform] BKHDBANHANG: NVQ02→NVQ03, NVQ03→VB, XKCTWFC01→XK")

        elif name == 'DMNHANVIENKD':
            # ma_bp fallback: no BP → XX (need BP from DMKHACHHANG, done at query time)
            # ma_ql fallback: has BP but no ma_ql → BP + "99" (done at query time)
            pass

        return table

    def run_once(self):
        """Chạy 1 lần sync. Return True nếu thành công."""
        started = datetime.now()
        logger.info(f"[DataSync] Bắt đầu sync {len(VIEW_REGISTRY)} views...")

        try:
            # 1. Kết nối SQL Server
            conn = self._get_connection()
            conn.autocommit = True

            # 2. Pull từng view → ghi staging
            # Xóa staging cũ
            if self.staging_dir.exists():
                shutil.rmtree(self.staging_dir)
            self.staging_dir.mkdir(parents=True, exist_ok=True)

            for vc in VIEW_REGISTRY:
                name = vc['name']
                try:
                    table = self._pull_view(conn, vc)
                    table = self._transform(name, table)
                    out_path = self.staging_dir / f'{name}.parquet'
                    pq.write_table(table, out_path, compression='snappy')
                    logger.info(f"  ✓ {name}: {table.num_rows} rows → {out_path.name}")
                except Exception as e:
                    logger.error(f"  ✗ {name}: {e}")
                    conn.close()
                    raise  # Abort toàn bộ lượt sync

            conn.close()

            # 3. Atomic swap: staging → current
            #    Rename current → backup, staging → current, xóa backup
            backup_dir = self.data_dir / '_backup'
            if backup_dir.exists():
                shutil.rmtree(backup_dir)

            if self.current_dir.exists():
                self.current_dir.rename(backup_dir)

            self.staging_dir.rename(self.current_dir)

            # Tạo lại staging dir (trống)
            self.staging_dir.mkdir(parents=True, exist_ok=True)

            # Xóa backup
            if backup_dir.exists():
                shutil.rmtree(backup_dir)

            elapsed = (datetime.now() - started).total_seconds()
            self.last_sync = datetime.now()
            self.last_error = None
            self.sync_count += 1
            logger.info(f"[DataSync] ✓ Sync #{self.sync_count} hoàn thành trong {elapsed:.1f}s")

            # Sync dimension history (SCD Type 2)
            try:
                from dim_history import sync_dim_history
                sync_dim_history(self.config)
            except Exception as dh_err:
                logger.error(f"[DataSync] DimHistory error (non-fatal): {dh_err}")

            # Gọi callback (ví dụ: reload DuckDB)
            if self.on_success:
                try:
                    self.on_success()
                except Exception as cb_err:
                    logger.error(f"[DataSync] on_success callback error: {cb_err}")

            return True

        except Exception as e:
            elapsed = (datetime.now() - started).total_seconds()
            self.last_error = str(e)
            logger.error(f"[DataSync] ✗ Sync thất bại sau {elapsed:.1f}s: {e}")
            # Cleanup staging (giữ nguyên current)
            if self.staging_dir.exists():
                shutil.rmtree(self.staging_dir)
                self.staging_dir.mkdir(parents=True, exist_ok=True)
            return False

    def _loop(self):
        """Background loop"""
        logger.info(f"[DataSync] Scheduler started: interval={self.interval}s")
        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(self.interval)
        logger.info("[DataSync] Scheduler stopped")

    def start(self):
        """Chạy sync lần đầu (blocking), rồi start background thread"""
        self.run_once()
        self.start_background()

    def start_background(self):
        """Chỉ start background scheduler (không chạy sync ngay)"""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name='data-sync')
        self._thread.start()

    def stop(self):
        """Dừng background scheduler"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def status(self):
        """Trả về trạng thái sync"""
        return {
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'last_error': self.last_error,
            'sync_count': self.sync_count,
            'interval': self.interval,
            'has_data': any(self.current_dir.glob('*.parquet')),
        }