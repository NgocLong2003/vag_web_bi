import sqlite3
import hashlib
from flask import g, request
from config import DB_TYPE, SQLITE_PATH, SQLSERVER_CONFIG, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASS


# ==============================================================
# SQL SERVER WRAPPER
# ==============================================================

def _get_sqlserver_conn():
    import pyodbc
    c = SQLSERVER_CONFIG
    return pyodbc.connect(
        f"DRIVER={{{c['driver']}}};SERVER={c['server']},{c['port']};"
        f"DATABASE={c['database']};UID={c['username']};PWD={c['password']};"
        "TrustServerCertificate=yes;", autocommit=False)


class _Row(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class _SqlServerDb:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        cur = self._conn.cursor()
        cur.execute(sql, params or [])
        return _Cursor(cur)

    def commit(self):
        self._conn.commit()

    def close(self):
        try: self._conn.close()
        except: pass


class _Cursor:
    def __init__(self, cur):
        self._cur = cur
        self.description = cur.description

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None: return None
        if self.description:
            return _Row({d[0]: row[i] for i, d in enumerate(self.description)})
        return row

    def fetchall(self):
        rows = self._cur.fetchall()
        if not self.description: return rows
        return [_Row({d[0]: r[i] for i, d in enumerate(self.description)}) for r in rows]


# ==============================================================
# PUBLIC API
# ==============================================================

def get_db():
    if 'db' not in g:
        if DB_TYPE == 'sqlserver':
            g.db = _SqlServerDb(_get_sqlserver_conn())
        else:
            g.db = sqlite3.connect(SQLITE_PATH)
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA journal_mode=WAL')
            g.db.execute('PRAGMA foreign_keys=ON')
    return g.db


def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None: db.close()


# ==============================================================
# SQL HELPERS
# ==============================================================

def sql_now():
    return "GETDATE()" if DB_TYPE == 'sqlserver' else "datetime('now','localtime')"

def sql_date_ago():
    if DB_TYPE == 'sqlserver':
        return "al.created_at >= DATEADD(day, -CAST(? AS INT), GETDATE())"
    return "al.created_at >= datetime('now','localtime',?)"

def sql_date_ago_param(days):
    return days if DB_TYPE == 'sqlserver' else f'-{days} days'

def sql_extract_date():
    return "CONVERT(DATE, al.created_at)" if DB_TYPE == 'sqlserver' else "date(al.created_at)"

def sql_extract_hour():
    return "DATEPART(HOUR, al.created_at)" if DB_TYPE == 'sqlserver' else "CAST(strftime('%H', al.created_at) AS INTEGER)"

def sql_limit(n=10):
    if DB_TYPE == 'sqlserver':
        return f"TOP {n}", ""
    return "", f"LIMIT {n}"


# ==============================================================
# UTILITY
# ==============================================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def log_activity(user_id, action, dashboard_id=None):
    try:
        db = get_db()
        db.execute(
            'INSERT INTO activity_log (user_id, action, dashboard_id, ip, user_agent) VALUES (?, ?, ?, ?, ?)',
            (user_id, action, dashboard_id,
             request.remote_addr or '',
             (request.user_agent.string if request.user_agent else '')[:200]))
        db.commit()
    except:
        pass


# ==============================================================
# INIT DB
# ==============================================================

def init_db():
    if DB_TYPE == 'sqlserver':
        try:
            conn = _get_sqlserver_conn()
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM users')
            if cur.fetchone()[0] == 0:
                cur.execute(
                    'INSERT INTO users (username, password_hash, password_plain, display_name, role) VALUES (?, ?, ?, ?, ?)',
                    (DEFAULT_ADMIN_USER, hash_password(DEFAULT_ADMIN_PASS), DEFAULT_ADMIN_PASS, 'Administrator', 'admin'))
            conn.commit(); conn.close()
            print('[OK] SQL Server connected')
        except Exception as e:
            print(f'[ERROR] SQL Server: {e}')
        return

    db = sqlite3.connect(SQLITE_PATH)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, password_plain TEXT DEFAULT '',
            display_name TEXT DEFAULT '', khoi TEXT DEFAULT '', bo_phan TEXT DEFAULT '',
            chuc_vu TEXT DEFAULT '', role TEXT DEFAULT 'user', is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')), last_login TEXT);
        CREATE TABLE IF NOT EXISTS dashboards (
            id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL, powerbi_url TEXT NOT NULL DEFAULT '', description TEXT DEFAULT '',
            dashboard_type TEXT DEFAULT 'powerbi',
            is_active INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS user_dashboards (
            user_id INTEGER NOT NULL, dashboard_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, dashboard_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (dashboard_id) REFERENCES dashboards(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            action TEXT NOT NULL, dashboard_id INTEGER, ip TEXT DEFAULT '',
            user_agent TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at);
        CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id);
    ''')
    for col in ['password_plain', 'khoi', 'bo_phan', 'chuc_vu']:
        try: db.execute(f'ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT ""')
        except: pass
    try: db.execute('ALTER TABLE dashboards ADD COLUMN dashboard_type TEXT DEFAULT "powerbi"')
    except: pass
    if db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
        db.execute('INSERT INTO users (username, password_hash, password_plain, display_name, role) VALUES (?, ?, ?, ?, ?)',
                   (DEFAULT_ADMIN_USER, hash_password(DEFAULT_ADMIN_PASS), DEFAULT_ADMIN_PASS, 'Administrator', 'admin'))
    db.commit(); db.close()