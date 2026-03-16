import os

SECRET_KEY = 'doi-thanh-chuoi-bi-mat-cua-long-o-day-abc123'
SESSION_TIMEOUT_MINUTES = 480

DB_TYPE = 'sqlserver'  # 'sqlite' hoặc 'sqlserver'

SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.db')

SQLSERVER_CONFIG = {
    'server': '192.168.4.91',
    'port': '1433',
    'database': 'VietAnhBI',
    'username': 'sa',
    'password': '123456a@',
    'driver': 'ODBC Driver 17 for SQL Server',
}

DEFAULT_ADMIN_USER = 'admin'
DEFAULT_ADMIN_PASS = 'vietanh@2026'

os.environ['TZ'] = 'Asia/Ho_Chi_Minh'
try:
    import time; time.tzset()
except:
    pass