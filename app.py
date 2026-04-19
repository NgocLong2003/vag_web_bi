"""
app.py — VietAnh BI Web Application
Chạy trên Máy B (web server). Không sync dữ liệu.

Dữ liệu Parquet được sync bởi sync_worker.py (Máy A).
App tự detect thay đổi Parquet → reload DuckDB.

Cấu trúc thư mục data/:
  data/current/*.parquet    ← DuckDB đọc từ đây
  data/sync_status.json     ← sync_worker ghi, app đọc để hiển thị trạng thái
"""

from waitress import serve
from datetime import timedelta, datetime
from flask import Flask, jsonify
from config import SECRET_KEY, SESSION_TIMEOUT_MINUTES
from database import init_db, close_db
from duckdb_store import DuckDBStore
import logging
import threading
import time
import json
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s'
)
logger = logging.getLogger('app')

app = Flask(__name__)
app.json.ensure_ascii = False
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['TEMPLATES_AUTO_RELOAD'] = True

app.teardown_appcontext(close_db)

# ─── DuckDB Store (đọc Parquet, không sync) ───
DATA_DIR = Path('data')
CURRENT_DIR = DATA_DIR / 'current'

store = DuckDBStore(data_dir=str(CURRENT_DIR))

# Load DuckDB lần đầu
if any(CURRENT_DIR.glob('*.parquet')):
    print('  Loading DuckDB từ Parquet...')
    store.load()
else:
    print('  ⚠ Chưa có data Parquet. Chờ sync_worker chạy.')

app.config['DUCKDB_STORE'] = store

# ─── [MỚI] Init DataSource registry ───
try:
    from config import DATASOURCES
    from datasource import init_datasources
    init_datasources(DATASOURCES, duckdb_store=store)
    print('  ✓ DataSources initialized')
except ImportError:
    print('  ⚠ DATASOURCES not in config.py, skip (chỉ dùng DuckDB qua get_store())')
except Exception as e:
    print(f'  ✗ DataSource init error: {e}')


# ─── File Watcher: detect Parquet changes → reload DuckDB ───
class ParquetWatcher:
    """Theo dõi thư mục Parquet, reload DuckDB khi có thay đổi."""

    def __init__(self, data_dir, store, check_interval=30):
        self.data_dir = Path(data_dir)
        self.store = store
        self.check_interval = check_interval
        self._last_mtime = self._get_max_mtime()
        self._stop = threading.Event()
        self._thread = None

    def _get_max_mtime(self):
        """Lấy mtime lớn nhất của các file Parquet."""
        try:
            files = list(self.data_dir.glob('*.parquet'))
            if not files:
                return 0
            return max(f.stat().st_mtime for f in files)
        except:
            return 0

    def _loop(self):
        while not self._stop.is_set():
            self._stop.wait(self.check_interval)
            if self._stop.is_set():
                break
            try:
                current_mtime = self._get_max_mtime()
                if current_mtime > self._last_mtime:
                    logger.info("[Watcher] Parquet files changed, reloading DuckDB...")
                    self.store.reload()
                    self._last_mtime = current_mtime
                    logger.info("[Watcher] DuckDB reloaded OK")
            except Exception as e:
                logger.error(f"[Watcher] Error: {e}")

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True, name='parquet-watcher')
        self._thread.start()
        logger.info(f"[Watcher] Started, checking every {self.check_interval}s")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)


watcher = ParquetWatcher(CURRENT_DIR, store, check_interval=30)
watcher.start()


# ─── Jinja filters ───
@app.template_filter('fmtd')
def fmtd_filter(d):
    if d is None:
        return ''
    s = str(d)[:10]
    if '-' in s:
        p = s.split('-')
        return f'{p[2]}/{p[1]}/{p[0]}'
    return s

app.jinja_env.globals['fmtd'] = fmtd_filter


@app.template_filter('fmtiso')
def fmtiso_filter(d):
    if d is None:
        return ''
    return str(d)[:10]

app.jinja_env.globals['fmtiso'] = fmtiso_filter


@app.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ─── Blueprints ───
from auth.routes import bp as auth_bp;       app.register_blueprint(auth_bp)
from dashboard import bp as dash_bp;         app.register_blueprint(dash_bp)
from admin import bp as admin_bp;            app.register_blueprint(admin_bp)
from analytics import bp as analytics_bp;    app.register_blueprint(analytics_bp)
from api_logger import init_api_logger
init_api_logger(app, ds_name='warehouse')

from reports import get_all_blueprints
for slug, report_bp in get_all_blueprints():
    app.register_blueprint(report_bp)


# ─── API: monitoring ───
@app.route('/api/data-status')
def api_data_status():
    # Đọc sync status từ file (ghi bởi sync_worker)
    sync_status = {}
    status_path = DATA_DIR / 'sync_status.json'
    try:
        if status_path.exists():
            with open(status_path) as f:
                sync_status = json.load(f)
    except:
        pass

    # [MỚI] Datasource status
    ds_status = {}
    try:
        from datasource import get_all_status
        ds_status = get_all_status()
    except:
        pass

    return jsonify({
        'sync': sync_status,
        'store': store.status(),
        'datasources': ds_status,
        'mode': 'web-only (sync_worker separate)',
    })


init_db()

if __name__ == '__main__':
    print('=' * 55)
    print('  VietAnh BI Dashboard (Web Only)')
    print('  http://localhost:5000')
    print()
    print('  Data: ' + str(CURRENT_DIR.resolve()))
    print('  DuckDB tables: ' + str(len(store.table_stats)))
    print('  Parquet watcher: every 30s')
    print('=' * 55)
    try:
        serve(app, host='0.0.0.0', port=5000, threads=8)
    finally:
        watcher.stop()
        store.close()
        # [MỚI] Đóng datasources
        try:
            from datasource import close_all
            close_all()
        except:
            pass