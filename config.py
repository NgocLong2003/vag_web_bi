"""
config.py — Cấu hình tập trung VietAnh BI
===========================================
Mọi connection, path, credential khai báo TẠI ĐÂY.
"""

import os

os.environ['TZ'] = 'Asia/Ho_Chi_Minh'
try:
    import time; time.tzset()
except:
    pass


# ═══════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════

SECRET_KEY = 'doi-thanh-chuoi-bi-mat-cua-long-o-day-abc123'
SESSION_TIMEOUT_MINUTES = 480
DEFAULT_ADMIN_USER = 'admin'
DEFAULT_ADMIN_PASS = 'vietanh@2026'

DB_TYPE = 'sqlserver'
SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.db')

# database.py dùng (backward compat)
SQLSERVER_CONFIG = {
    'server': '192.168.4.17',
    'port': '1433',
    'database': 'VietAnhBI',
    'username': 'sa',
    'password': '123456a@',
    'driver': 'ODBC Driver 17 for SQL Server',
}


# ═══════════════════════════════════════════════════════
# DATASOURCES — registry duy nhất cho toàn bộ hệ thống
#
# Naming: <nguồn>.<vai_trò>
#   source.*    = ELT extract đọc (nguồn thô)
#   bronze.*    = ELT transform đọc (data thô đã extract)
#   silver      = App đọc (data đã merge)
#   gold        = App đọc (pre-aggregated, tương lai)
#   app.*       = App runtime (admin, logging)
#
# Types: 'sqlserver', 'rest_api', 'duckdb'
# ═══════════════════════════════════════════════════════

DATASOURCES = {

    # ── ELT: nguồn dữ liệu (extract đọc) ──────────────

    'source.asia': {
        'type': 'sqlserver',
        'server': '192.168.4.17',
        'port': '1433',
        'database': 'VietAnhBI',
        'username': 'sa',
        'password': '123456a@',
        'driver': 'ODBC Driver 17 for SQL Server',
    },

    'source.cns': {
        'type': 'rest_api',
        'base_url': 'http://113.190.242.246:8086',
        'auth_path': '/auth/token',
        'api_path': '/api',
        'username': 'admin',
        'password': 'CNS@Vietnam.2009',
        'client_id': 'bc989378a62549e9a918df74b59d3f36',
        'start_date': '2024-01-01',
        'ma_tk': '131',
    },

    # ── Lake: Parquet layers (ELT ghi, App đọc) ────────

    'bronze.asia': {
        'type': 'duckdb',
        'data_dir': 'data/bronze/asia',
    },

    'bronze.cns': {
        'type': 'duckdb',
        'data_dir': 'data/bronze/cns',
    },

    'silver': {
        'type': 'duckdb',
        'data_dir': 'data/silver',
    },

    'gold': {
        'type': 'duckdb',
        'data_dir': 'data/gold',
    },

    # ── App: runtime connections ────────────────────────

    'default': {
        'type': 'duckdb',
        'data_dir': 'data/silver',
    },

    'app.database': {
        'type': 'sqlserver',
        'server': '192.168.4.17',
        'port': '1433',
        'database': 'VietAnhBI',
        'username': 'sa',
        'password': '123456a@',
        'driver': 'ODBC Driver 17 for SQL Server',
        'pool_size': 3,
    },

    'warehouse': {
        'type': 'sqlserver',
        'server': '192.168.4.17',
        'port': '1433',
        'database': 'VietAnhBI',
        'username': 'sa',
        'password': '123456a@',
        'driver': 'ODBC Driver 17 for SQL Server',
        'pool_size': 3,
    },

    'sanxuat': {
        'type': 'sqlserver',
        'server': '192.168.4.220',
        'port': '5678',
        'database': 'AE1213VietAnhDATA',
        'username': 'long',
        'password': '12345',
        'driver': 'ODBC Driver 17 for SQL Server',
        'pool_size': 3,
    },
}


# ═══════════════════════════════════════════════════════
# PIPELINE
# ═══════════════════════════════════════════════════════

PIPELINE = {
    'interval': 1800,
    'health_port': 5001,
}