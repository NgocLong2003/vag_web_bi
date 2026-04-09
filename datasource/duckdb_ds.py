"""
datasource/duckdb_ds.py — DuckDB DataSource (wrap DuckDBStore hiện có).
Dùng cho batch reports (Parquet-backed).
"""
from datasource.base import DataSource


class DuckDBDataSource(DataSource):
    """Thin wrapper quanh DuckDBStore để conform DataSource interface."""

    def __init__(self, store):
        """
        Args:
            store: DuckDBStore instance (đã load sẵn)
        """
        self._store = store

    def query(self, sql, params=None):
        return self._store.query(sql, params)

    def query_raw(self, sql, params=None):
        return self._store.query_raw(sql, params)

    def status(self):
        s = self._store.status()
        s['type'] = 'duckdb'
        return s