"""
query_loader.py — Load SQL files từ queries/ folder

Usage:
    from query_loader import load_sql
    sql = load_sql('DOANHSO_SQL_DUCK')  # → đọc queries/DOANHSO_SQL_DUCK.sql
"""

import os
from pathlib import Path
from functools import lru_cache

QUERIES_DIR = Path(__file__).parent / 'queries'


@lru_cache(maxsize=None)
def load_sql(name):
    """
    Load SQL từ file queries/{name}.sql
    Cache vĩnh viễn (file không thay đổi runtime).
    """
    path = QUERIES_DIR / f'{name}.sql'
    if not path.exists():
        raise FileNotFoundError(f"Query file not found: {path}")
    return path.read_text(encoding='utf-8').strip()