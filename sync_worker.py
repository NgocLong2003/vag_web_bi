"""
sync_worker.py — Standalone Data Sync Worker
Chạy trên Máy A (sync machine). Không cần Flask.

Chức năng:
  1. Kết nối SQL Server → pull views → transform → ghi Parquet
  2. Sync dim_history (SCD Type 2)
  3. Lặp lại mỗi N phút
  4. HTTP health endpoint (optional) để Máy B kiểm tra trạng thái

Usage:
  python sync_worker.py                    # chạy liên tục, 30 phút/lần
  python sync_worker.py --once             # chạy 1 lần rồi thoát
  python sync_worker.py --interval 600     # 10 phút/lần
  python sync_worker.py --port 5001        # health check trên port 5001

Config:
  Đọc từ config.py (cùng thư mục dự án)
"""

import os
import sys
import time
import json
import argparse
import logging
import threading
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s'
)
logger = logging.getLogger('sync_worker')


def main():
    parser = argparse.ArgumentParser(description='VietAnh BI — Data Sync Worker')
    parser.add_argument('--once', action='store_true', help='Chạy 1 lần rồi thoát')
    parser.add_argument('--interval', type=int, default=1800, help='Giây giữa các lần sync (mặc định: 1800 = 30 phút)')
    parser.add_argument('--data-dir', type=str, default='data', help='Thư mục data (mặc định: data)')
    parser.add_argument('--port', type=int, default=0, help='Port cho health check HTTP (0 = tắt)')
    args = parser.parse_args()

    # Load config
    try:
        from config import SQLSERVER_CONFIG
    except ImportError:
        logger.error("Không tìm thấy config.py hoặc SQLSERVER_CONFIG")
        sys.exit(1)

    from data_sync import DataSync

    # Trạng thái để health check
    status = {
        'started_at': datetime.now().isoformat(),
        'last_sync': None,
        'last_error': None,
        'sync_count': 0,
        'interval': args.interval,
        'pid': os.getpid(),
    }

    def on_sync_success():
        """Callback sau mỗi sync thành công."""
        status['last_sync'] = datetime.now().isoformat()
        status['sync_count'] += 1
        status['last_error'] = None

        # Ghi status file để Máy B đọc được
        status_path = Path(args.data_dir) / 'sync_status.json'
        try:
            with open(status_path, 'w') as f:
                json.dump(status, f, indent=2)
        except:
            pass

    sync = DataSync(
        sqlserver_config=SQLSERVER_CONFIG,
        data_dir=args.data_dir,
        interval=args.interval,
        on_success=on_sync_success,
    )

    # Health check HTTP server (optional)
    if args.port:
        start_health_server(args.port, status, sync)

    print('=' * 55)
    print('  VietAnh BI — Data Sync Worker')
    print(f'  PID: {os.getpid()}')
    print(f'  Data dir: {os.path.abspath(args.data_dir)}')
    print(f'  Interval: {args.interval}s ({args.interval // 60} phút)')
    if args.port:
        print(f'  Health check: http://localhost:{args.port}/status')
    print('=' * 55)

    if args.once:
        logger.info("Chạy sync 1 lần...")
        ok = sync.run_once()
        if ok:
            on_sync_success()
        sys.exit(0 if ok else 1)

    # Chạy liên tục
    logger.info(f"Bắt đầu sync loop, interval={args.interval}s")
    try:
        while True:
            ok = sync.run_once()
            if ok:
                on_sync_success()
            else:
                status['last_error'] = sync.last_error
                # Ghi status kể cả khi lỗi
                status_path = Path(args.data_dir) / 'sync_status.json'
                try:
                    with open(status_path, 'w') as f:
                        json.dump(status, f, indent=2)
                except:
                    pass

            logger.info(f"Ngủ {args.interval}s...")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("Dừng sync worker (Ctrl+C)")
        sys.exit(0)


def start_health_server(port, status, sync):
    """Mini HTTP server trả về JSON status."""
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/status':
                data = {**status, 'sync_detail': sync.status()}
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data, indent=2).encode())
            elif self.path == '/trigger':
                # Manual trigger sync
                threading.Thread(target=sync.run_once, daemon=True).start()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"ok": true, "message": "Sync triggered"}')
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # Suppress HTTP logs

    server = HTTPServer(('0.0.0.0', port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True, name='health-check')
    t.start()
    logger.info(f"Health check server started on port {port}")


if __name__ == '__main__':
    main()