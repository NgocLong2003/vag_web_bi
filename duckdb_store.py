"""
duckdb_store.py — DuckDB wrapper đọc Parquet, phục vụ query

Thiết kế:
  - Tạo DuckDB in-memory
  - Load Parquet → tạo VIEW (không copy data, DuckDB đọc trực tiếp Parquet)
  - Khi data_sync swap xong → gọi reload() để refresh views
  - Thread-safe: mỗi query tạo cursor riêng

Usage:
    from duckdb_store import DuckDBStore
    store = DuckDBStore('data/current')
    store.load()
    rows = store.query("SELECT * FROM DMKHACHHANG WHERE ma_bp = ?", ['VA'])
    store.reload()  # sau khi data_sync swap
"""

import os
import logging
import threading
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

import duckdb

logger = logging.getLogger(__name__)


class DuckDBStore:
    def __init__(self, data_dir='data/current'):
        self.data_dir = Path(data_dir)
        self._lock = threading.Lock()
        self._conn = None
        self.loaded_at = None
        self.table_stats = {}

    def load(self):
        """Load/reload tất cả Parquet files thành DuckDB views"""
        with self._lock:
            # Tạo connection mới (in-memory)
            if self._conn:
                try:
                    self._conn.close()
                except:
                    pass

            self._conn = duckdb.connect(':memory:')
            self.table_stats = {}

            parquet_files = list(self.data_dir.glob('*.parquet'))
            if not parquet_files:
                logger.warning(f"[DuckDB] Không có file Parquet trong {self.data_dir}")
                return

            for pf in parquet_files:
                table_name = pf.stem  # DMKHACHHANG.parquet → DMKHACHHANG
                try:
                    self._conn.execute(
                        f"CREATE OR REPLACE VIEW {table_name} AS "
                        f"SELECT * FROM read_parquet('{pf.as_posix()}')"
                    )
                    count = self._conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    self.table_stats[table_name] = count
                    logger.info(f"  ✓ {table_name}: {count:,} rows")
                except Exception as e:
                    logger.error(f"  ✗ {table_name}: {e}")

            self.loaded_at = datetime.now()
            logger.info(f"[DuckDB] Loaded {len(self.table_stats)} tables")

    def reload(self):
        """Alias cho load() — gọi sau khi data_sync swap xong"""
        logger.info("[DuckDB] Reloading...")
        self.load()

    def query(self, sql, params=None):
        """
        Chạy SQL query, trả về list of dict.
        Thread-safe.

        Args:
            sql: DuckDB SQL (dùng ? cho params hoặc $1, $2)
            params: list/tuple params (optional)

        Returns:
            list[dict] — mỗi row là 1 dict {column: value}
        """
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
        """
        Chạy SQL, trả về (columns, rows) — cho trường hợp cần tùy biến.
        """
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
        """Đảm bảo tất cả values JSON-safe"""
        for k, v in d.items():
            if isinstance(v, (datetime, date)):
                d[k] = v.isoformat()
            elif isinstance(v, Decimal):
                d[k] = float(v)
            elif v is not None and not isinstance(v, (str, int, float, bool)):
                d[k] = str(v)
        return d

    def status(self):
        """Trả về trạng thái store"""
        return {
            'loaded_at': self.loaded_at.isoformat() if self.loaded_at else None,
            'tables': self.table_stats,
            'total_rows': sum(self.table_stats.values()),
        }

    def close(self):
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None