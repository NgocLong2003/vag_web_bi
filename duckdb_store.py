"""
duckdb_store.py — DuckDB wrapper đọc Parquet / Delta Lake

Hỗ trợ 2 chế độ (tự detect):
  - Flat Parquet: data/current/*.parquet           (cũ, data_sync.py)
  - Delta Lake:   data/silver/TABLE/_delta_log/    (mới, elt pipeline)

Usage:
    store = DuckDBStore('data/silver')   # Delta Lake
    store = DuckDBStore('data/current')  # Flat Parquet (backward compat)
    store.load()
    rows = store.query("SELECT * FROM DMKHACHHANG WHERE ma_bp = ?", ['VA'])
"""

import logging
import threading
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

import duckdb

logger = logging.getLogger(__name__)


def _posix(path):
    """Convert Path → forward-slash absolute string (cross-platform cho DuckDB SQL)."""
    return Path(path).resolve().as_posix()


class DuckDBStore:
    def __init__(self, data_dir='data/current'):
        self.data_dir = Path(data_dir)
        self._lock = threading.Lock()
        self._conn = None
        self.loaded_at = None
        self.table_stats = {}
        self._mode = None  # 'delta' hoặc 'flat'

    def _detect_mode(self):
        """Detect xem data_dir chứa flat parquet hay Delta tables."""
        if not self.data_dir.exists():
            return None
        for d in self.data_dir.iterdir():
            if d.is_dir() and (d / '_delta_log').exists():
                return 'delta'
        if list(self.data_dir.glob('*.parquet')):
            return 'flat'
        return None

    def _load_delta(self, conn):
        """Load Delta Lake tables: dùng DeltaTable để lấy đúng parquet files."""
        try:
            from deltalake import DeltaTable
        except ImportError:
            logger.error("[DuckDB] deltalake chưa cài. pip install deltalake")
            return

        for table_dir in sorted(self.data_dir.iterdir()):
            if not table_dir.is_dir():
                continue
            if not (table_dir / '_delta_log').exists():
                continue

            table_name = table_dir.name
            try:
                dt = DeltaTable(str(table_dir.resolve()))
                file_uris = dt.file_uris()

                if not file_uris:
                    logger.warning(f"  ⊘ {table_name}: no files")
                    continue

                # Convert tất cả paths sang forward-slash absolute
                clean_paths = [_posix(f) for f in file_uris]

                if len(clean_paths) == 1:
                    sql = (f"CREATE OR REPLACE VIEW {table_name} AS "
                           f"SELECT * FROM read_parquet('{clean_paths[0]}')")
                else:
                    files_str = ", ".join(f"'{p}'" for p in clean_paths)
                    sql = (f"CREATE OR REPLACE VIEW {table_name} AS "
                           f"SELECT * FROM read_parquet([{files_str}])")

                conn.execute(sql)
                count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                self.table_stats[table_name] = count
                logger.info(f"  ✓ {table_name}: {count:,} rows (v{dt.version()})")

            except Exception as e:
                logger.error(f"  ✗ {table_name}: {e}")

    def _load_flat(self, conn):
        """Load flat Parquet files (backward compat với data/current/)."""
        for pf in sorted(self.data_dir.glob('*.parquet')):
            table_name = pf.stem
            try:
                posix_path = _posix(pf)
                conn.execute(
                    f"CREATE OR REPLACE VIEW {table_name} AS "
                    f"SELECT * FROM read_parquet('{posix_path}')"
                )
                count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                self.table_stats[table_name] = count
                logger.info(f"  ✓ {table_name}: {count:,} rows")
            except Exception as e:
                logger.error(f"  ✗ {table_name}: {e}")

    def load(self):
        """Load/reload: detect mode, tạo DuckDB views."""
        with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                except:
                    pass

            self._conn = duckdb.connect(':memory:')
            self.table_stats = {}
            self._mode = self._detect_mode()

            if self._mode == 'delta':
                logger.info(f"[DuckDB] Loading Delta Lake from {self.data_dir}")
                self._load_delta(self._conn)
            elif self._mode == 'flat':
                logger.info(f"[DuckDB] Loading flat Parquet from {self.data_dir}")
                self._load_flat(self._conn)
            else:
                logger.warning(f"[DuckDB] Không có data trong {self.data_dir}")

            self.loaded_at = datetime.now()
            logger.info(f"[DuckDB] Loaded {len(self.table_stats)} tables ({self._mode} mode)")

    def reload(self):
        """Reload zero-downtime: tạo conn mới, swap, đóng cũ sau 5s."""
        new_conn = duckdb.connect(':memory:')
        new_stats = {}

        mode = self._detect_mode()

        if mode == 'delta':
            try:
                from deltalake import DeltaTable
            except ImportError:
                new_conn.close()
                return
            for table_dir in sorted(self.data_dir.iterdir()):
                if not table_dir.is_dir() or not (table_dir / '_delta_log').exists():
                    continue
                table_name = table_dir.name
                try:
                    dt = DeltaTable(str(table_dir.resolve()))
                    file_uris = dt.file_uris()
                    if not file_uris:
                        continue
                    clean_paths = [_posix(f) for f in file_uris]
                    if len(clean_paths) == 1:
                        sql = (f"CREATE OR REPLACE VIEW {table_name} AS "
                               f"SELECT * FROM read_parquet('{clean_paths[0]}')")
                    else:
                        files_str = ", ".join(f"'{p}'" for p in clean_paths)
                        sql = (f"CREATE OR REPLACE VIEW {table_name} AS "
                               f"SELECT * FROM read_parquet([{files_str}])")
                    new_conn.execute(sql)
                    count = new_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    new_stats[table_name] = count
                except Exception as e:
                    logger.error(f"  ✗ {table_name}: {e}")

        elif mode == 'flat':
            for pf in sorted(self.data_dir.glob('*.parquet')):
                table_name = pf.stem
                try:
                    posix_path = _posix(pf)
                    new_conn.execute(
                        f"CREATE OR REPLACE VIEW {table_name} AS "
                        f"SELECT * FROM read_parquet('{posix_path}')"
                    )
                    count = new_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    new_stats[table_name] = count
                except Exception as e:
                    logger.error(f"  ✗ {table_name}: {e}")

        # Atomic swap
        with self._lock:
            old_conn = self._conn
            self._conn = new_conn
            self.table_stats = new_stats
            self._mode = mode
            self.loaded_at = datetime.now()

        if old_conn:
            def _close_old():
                import time
                time.sleep(5)
                try:
                    old_conn.close()
                except:
                    pass
            threading.Thread(target=_close_old, daemon=True).start()

        logger.info(f"[DuckDB] Reloaded {len(new_stats)} tables ({mode} mode)")

    def query(self, sql, params=None):
        """Chạy SQL query, trả về list of dict. Thread-safe."""
        with self._lock:
            if not self._conn:
                raise RuntimeError("DuckDB chưa load. Gọi store.load() trước.")
            try:
                if params:
                    result = self._conn.execute(sql, params)
                else:
                    result = self._conn.execute(sql)

                if not result.description:
                    return []

                columns = [desc[0] for desc in result.description]
                rows = result.fetchall()
                return [self._serialize(dict(zip(columns, row))) for row in rows]

            except Exception as e:
                logger.error(f"[DuckDB] Query error: {e}\nSQL: {sql[:200]}")
                raise

    def query_raw(self, sql, params=None):
        """Chạy SQL, trả về (columns, rows)."""
        with self._lock:
            if not self._conn:
                raise RuntimeError("DuckDB chưa load.")
            if params:
                result = self._conn.execute(sql, params)
            else:
                result = self._conn.execute(sql)
            if not result.description:
                return [], []
            columns = [desc[0] for desc in result.description]
            return columns, result.fetchall()

    def _serialize(self, d):
        for k, v in d.items():
            if isinstance(v, (datetime, date)):
                d[k] = v.isoformat()
            elif isinstance(v, Decimal):
                d[k] = float(v)
            elif v is not None and not isinstance(v, (str, int, float, bool)):
                d[k] = str(v)
        return d

    def status(self):
        return {
            'loaded_at': self.loaded_at.isoformat() if self.loaded_at else None,
            'tables': self.table_stats,
            'total_rows': sum(self.table_stats.values()),
            'mode': self._mode,
            'data_dir': str(self.data_dir),
        }

    def close(self):
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None