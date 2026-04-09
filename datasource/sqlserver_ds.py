"""
datasource/sqlserver_ds.py — SQL Server direct query DataSource.
Connection pool (queue-based) để reuse connections.
Dùng cho realtime reports.
"""
import queue
import logging
import threading
from datetime import datetime, date
from decimal import Decimal

import pyodbc

from datasource.base import DataSource

logger = logging.getLogger(__name__)


class SQLServerDataSource(DataSource):

    def __init__(self, config, pool_size=3):
        """
        Args:
            config: dict với keys: server, port, database, username, password, driver
            pool_size: số connections trong pool
        """
        self.config = config
        self.pool_size = pool_size
        self._pool = queue.Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created = 0
        self._query_count = 0
        self._last_query = None

        # Pre-fill pool
        for _ in range(pool_size):
            try:
                conn = self._create_conn()
                self._pool.put(conn)
                self._created += 1
            except Exception as e:
                logger.error(f"[SQLServerDS] Failed to create connection: {e}")

        logger.info(f"[SQLServerDS] Pool ready: {self._created}/{pool_size} connections "
                     f"→ {config.get('server')}:{config.get('port')}/{config.get('database')}")

    def _create_conn(self):
        c = self.config
        conn = pyodbc.connect(
            f"DRIVER={{{c['driver']}}};SERVER={c['server']},{c['port']};"
            f"DATABASE={c['database']};UID={c['username']};PWD={c['password']};"
            "TrustServerCertificate=yes;Connect Timeout=15;",
            timeout=15,
            autocommit=True
        )
        return conn

    def _get_conn(self):
        """Lấy connection từ pool, tạo mới nếu pool rỗng."""
        try:
            conn = self._pool.get(timeout=10)
            # Test connection
            try:
                conn.execute("SELECT 1")
            except:
                # Connection dead, tạo mới
                try:
                    conn.close()
                except:
                    pass
                conn = self._create_conn()
            return conn
        except queue.Empty:
            # Pool rỗng, tạo connection tạm
            logger.warning("[SQLServerDS] Pool exhausted, creating temp connection")
            return self._create_conn()

    def _return_conn(self, conn):
        """Trả connection về pool."""
        try:
            self._pool.put_nowait(conn)
        except queue.Full:
            # Pool đầy, đóng connection thừa
            try:
                conn.close()
            except:
                pass

    def query(self, sql, params=None):
        """Chạy SQL, trả về list[dict]."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)

            if not cur.description:
                return []

            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            self._query_count += 1
            self._last_query = datetime.now()

            return [self._serialize(dict(zip(columns, row))) for row in rows]
        except Exception as e:
            logger.error(f"[SQLServerDS] Query error: {e}\nSQL: {sql[:200]}")
            # Connection có thể bị hỏng, đóng và tạo mới
            try:
                conn.close()
            except:
                pass
            conn = self._create_conn()
            raise
        finally:
            self._return_conn(conn)

    def query_raw(self, sql, params=None):
        """Chạy SQL, trả về (columns, rows)."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)

            if not cur.description:
                return [], []

            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            self._query_count += 1
            self._last_query = datetime.now()
            return columns, rows
        except Exception as e:
            logger.error(f"[SQLServerDS] Query error: {e}")
            try:
                conn.close()
            except:
                pass
            conn = self._create_conn()
            raise
        finally:
            self._return_conn(conn)

    def _serialize(self, d):
        """JSON-safe serialization."""
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
            'type': 'sqlserver',
            'server': f"{self.config.get('server')}:{self.config.get('port')}",
            'database': self.config.get('database'),
            'pool_size': self.pool_size,
            'pool_available': self._pool.qsize(),
            'query_count': self._query_count,
            'last_query': self._last_query.isoformat() if self._last_query else None,
        }

    def close(self):
        """Đóng tất cả connections trong pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except:
                pass