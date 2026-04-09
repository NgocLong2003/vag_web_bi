"""
datasource/base.py — Abstract DataSource interface.
Tất cả datasource (DuckDB, SQL Server, API...) đều implement interface này.
"""
from abc import ABC, abstractmethod


class DataSource(ABC):

    @abstractmethod
    def query(self, sql, params=None):
        """Chạy SQL, trả về list[dict]."""
        pass

    @abstractmethod
    def query_raw(self, sql, params=None):
        """Chạy SQL, trả về (columns, rows)."""
        pass

    @abstractmethod
    def status(self):
        """Trả về dict trạng thái."""
        pass