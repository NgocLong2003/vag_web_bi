import os

SECRET_KEY = 'doi-thanh-chuoi-bi-mat-cua-long-o-day-abc123'
SESSION_TIMEOUT_MINUTES = 480

DB_TYPE = 'sqlserver'  # 'sqlite' hoặc 'sqlserver'

SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.db')

SQLSERVER_CONFIG = {
    'server': '192.168.4.16',
    'port': '1433',
    'database': 'VietAnhBI',
    'username': 'sa',
    'password': '123456a@',
    'driver': 'ODBC Driver 17 for SQL Server',
}

# Server kế toán (nguồn dữ liệu cho DataSync → Parquet)
SQLSERVER_DATA_CONFIG = {
    'server': '192.168.4.220',
    'port': '5678',
    'database': 'AE1213VietAnhDATA',
    'username': 'long',
    'password': '12345',
    'driver': 'ODBC Driver 17 for SQL Server',
}

# ─── DataSource Registry ───
DATASOURCES = {
    # Batch: DuckDB đọc Parquet (sync mỗi 30 phút từ SQLSERVER_DATA_CONFIG)
    'default': {
        'type': 'duckdb',
        'data_dir': 'data/current',
    },

    # Realtime: trỏ thẳng vào SQL Server kế toán (dùng cho báo cáo cần dữ liệu tức thì)
    # 'ketoan': {
    #     'type': 'sqlserver',
    #     'server': '192.168.4.220',
    #     'port': '5678',
    #     'database': 'AE1213VietAnhDATA',
    #     'username': 'long',
    #     'password': '12345',
    #     'driver': 'ODBC Driver 17 for SQL Server',
    #     'pool_size': 3,
    # },

    # Realtime: SQL Server kế hoạch sản xuất
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

DEFAULT_ADMIN_USER = 'admin'
DEFAULT_ADMIN_PASS = 'vietanh@2026'

os.environ['TZ'] = 'Asia/Ho_Chi_Minh'
try:
    import time; time.tzset()
except:
    pass