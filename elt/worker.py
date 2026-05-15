"""
elt/worker.py — Scheduler loop
================================
Chạy pipeline theo lịch. Hỗ trợ per-task intervals.

Usage:
    python run_worker.py
"""

import json
import logging
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from config import DATASOURCES, PIPELINE
from elt.pipeline import run_pipeline

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, interval=None, health_port=None, on_success=None):
        """
        Args:
            interval:    giây giữa các lần chạy (default từ config.PIPELINE)
            health_port: port HTTP health check (0 = tắt)
            on_success:  callback sau mỗi pipeline thành công
        """
        self.interval = interval or PIPELINE.get('interval', 1800)
        self.health_port = health_port if health_port is not None else PIPELINE.get('health_port', 0)
        self.on_success = on_success

        self._stop_event = threading.Event()
        self._thread = None
        self._health_server = None

        # Status
        self.last_run = None
        self.last_error = None
        self.run_count = 0
        self.status_file = Path('data/sync_status.json')

    def run_once(self):
        """Chạy pipeline 1 lần."""
        started = datetime.now()
        logger.info(f"[Worker] Pipeline #{self.run_count + 1} bắt đầu")

        try:
            result = run_pipeline()
            self.run_count += 1
            self.last_run = datetime.now()

            if result['status'] in ('ok', 'partial'):
                self.last_error = None
                if self.on_success:
                    try:
                        self.on_success()
                    except Exception as e:
                        logger.error(f"[Worker] on_success error: {e}")
            else:
                self.last_error = f"Pipeline status: {result['status']}"

            self._save_status(result)
            return result

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"[Worker] Pipeline failed: {e}")
            return None

    def _save_status(self, result):
        """Ghi sync_status.json."""
        try:
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            status = {
                'last_run': self.last_run.isoformat() if self.last_run else None,
                'last_error': self.last_error,
                'run_count': self.run_count,
                'pipeline_status': result.get('status'),
                'pipeline_seconds': result.get('seconds'),
                'extract_asia_count': len(result.get('extract_asia', [])),
                'extract_cns_count': len(result.get('extract_cns', [])),
                'transform_count': len(result.get('transform', [])),
            }
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"[Worker] save_status error: {e}")

    def _loop(self):
        """Background loop."""
        while not self._stop_event.is_set():
            self.run_once()
            logger.info(f"[Worker] Ngủ {self.interval}s...")
            self._stop_event.wait(self.interval)

    def start(self):
        """Chạy 1 lần rồi start background loop + health check."""
        self.run_once()
        self.start_background()

    def start_background(self):
        """Start background scheduler."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name='elt-worker')
        self._thread.start()

        if self.health_port:
            self._start_health_server()

    def stop(self):
        """Dừng scheduler."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self._health_server:
            self._health_server.shutdown()

    def _start_health_server(self):
        """HTTP health check endpoint."""
        worker = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                status = {
                    'status': 'ok',
                    'last_run': worker.last_run.isoformat() if worker.last_run else None,
                    'last_error': worker.last_error,
                    'run_count': worker.run_count,
                    'interval': worker.interval,
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(status).encode())

            def log_message(self, *args):
                pass  # Suppress HTTP log

        try:
            self._health_server = HTTPServer(('0.0.0.0', self.health_port), Handler)
            t = threading.Thread(target=self._health_server.serve_forever, daemon=True, name='health')
            t.start()
            logger.info(f"[Worker] Health check: http://0.0.0.0:{self.health_port}/")
        except Exception as e:
            logger.warning(f"[Worker] Health server failed: {e}")