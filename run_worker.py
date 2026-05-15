"""
run_worker.py — Entry point cho ELT worker (Máy A)
====================================================
    python run_worker.py
"""

import logging
import os
import sys
import signal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
)

from config import PIPELINE
from elt.worker import Worker


def main():
    interval = PIPELINE.get('interval', 1800)
    health_port = PIPELINE.get('health_port', 0)

    print("=" * 55)
    print("  VietAnh BI — ELT Worker")
    print(f"  PID: {os.getpid()}")
    print(f"  Interval: {interval}s ({interval // 60} phút)")
    if health_port:
        print(f"  Health: http://0.0.0.0:{health_port}/")
    print("=" * 55)

    worker = Worker(interval=interval, health_port=health_port)

    # Graceful shutdown
    def shutdown(sig, frame):
        print("\n[Worker] Shutting down...")
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Chạy lần đầu + start loop
    worker.start()

    # Block main thread
    try:
        while True:
            signal.pause()
    except AttributeError:
        # Windows không có signal.pause
        while True:
            try:
                import time
                time.sleep(1)
            except KeyboardInterrupt:
                shutdown(None, None)


if __name__ == '__main__':
    main()