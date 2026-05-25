"""
elt/extract/base.py — Shared utilities cho extractors
=======================================================
ExtractResult, checksums, change detection, atomic swap, helpers.
Không chứa connection logic (xem elt/connections.py).
"""

import hashlib
import json
import logging
import re
import shutil
import time as _time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

_ILLEGAL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


# ═══════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════

@dataclass
class ExtractResult:
    """Kết quả extract 1 bảng."""
    table: str
    layer: str = ''
    rows: int = 0
    seconds: float = 0
    status: str = 'ok'
    error: Optional[str] = None
    changes: Optional[dict] = None
    hash: Optional[str] = None
    optional: bool = False
    detail: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != '' and v != []}


# ═══════════════════════════════════════════════════════
# PARQUET I/O
# ═══════════════════════════════════════════════════════

def write_parquet(df, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, str(path), compression='snappy')


def read_parquet(path):
    path = Path(path)
    if not path.exists():
        return None
    return pd.read_parquet(path)


# ═══════════════════════════════════════════════════════
# CLEAN
# ═══════════════════════════════════════════════════════

def clean_df(df):
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(
            lambda x: _ILLEGAL_CHARS_RE.sub('', x) if isinstance(x, str) else x
        )
    return df


# ═══════════════════════════════════════════════════════
# CHECKSUMS & CHANGE DETECTION
# ═══════════════════════════════════════════════════════

def table_hash(df):
    if df is None or df.empty:
        return None
    raw = pd.util.hash_pandas_object(df).values.tobytes()
    return hashlib.sha256(raw).hexdigest()[:16]


def detect_changes(df_new, df_old, pk_col):
    if df_old is None or df_old.empty:
        return {"added": len(df_new), "updated": 0, "deleted": 0}
    if df_new is None or df_new.empty:
        return {"added": 0, "updated": 0, "deleted": len(df_old)}

    old_keys = set(df_old[pk_col].astype(str))
    new_keys = set(df_new[pk_col].astype(str))
    added = len(new_keys - old_keys)
    deleted = len(old_keys - new_keys)
    common = new_keys & old_keys

    updated = 0
    if common:
        old_idx = df_old.set_index(df_old[pk_col].astype(str))
        new_idx = df_new.set_index(df_new[pk_col].astype(str))
        for key in common:
            try:
                if not old_idx.loc[key].equals(new_idx.loc[key]):
                    updated += 1
            except Exception:
                updated += 1

    return {"added": added, "updated": updated, "deleted": deleted}


def has_changes(changes):
    if not changes:
        return False
    return sum(changes.get(k, 0) for k in ("added", "updated", "deleted")) > 0


# ═══════════════════════════════════════════════════════
# CHECKSUMS FILE
# ═══════════════════════════════════════════════════════

def load_checksums(meta_dir):
    path = Path(meta_dir) / "checksums.json"
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_checksums(meta_dir, checksums):
    path = Path(meta_dir) / "checksums.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(checksums, f, indent=2, ensure_ascii=False, default=str)


def update_checksum(checksums, table_name, df, changes=None):
    h = table_hash(df)
    old = checksums.get(table_name, {})
    old_hash = old.get("hash")
    now = datetime.now().isoformat()
    checksums[table_name] = {
        "row_count": len(df) if df is not None else 0,
        "hash": h,
        "last_synced": now,
        "last_changed": now if h != old_hash else old.get("last_changed", now),
        "hash_changed": h != old_hash,
    }
    if changes:
        checksums[table_name]["changes"] = changes
    return h != old_hash


# ═══════════════════════════════════════════════════════
# ATOMIC SWAP
# ═══════════════════════════════════════════════════════

def atomic_swap(staging_dir, target_dir, backup_dir=None):
    staging_dir = Path(staging_dir)
    target_dir = Path(target_dir)
    backup_dir = Path(backup_dir) if backup_dir else target_dir.parent / f"_backup_{target_dir.name}"

    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    try:
        if target_dir.exists():
            target_dir.rename(backup_dir)
        staging_dir.rename(target_dir)
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
    except Exception as e:
        if backup_dir.exists() and not target_dir.exists():
            backup_dir.rename(target_dir)
        raise RuntimeError(f"atomic_swap failed: {e}") from e


def ensure_dirs(*dirs):
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════

def months_between(start_str, end_str):
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_str, "%Y-%m-%d").date()
    result = []
    cursor = start.replace(day=1)
    while cursor <= end:
        month_start = max(cursor, start)
        if cursor.month == 12:
            next_month = cursor.replace(year=cursor.year + 1, month=1)
        else:
            next_month = cursor.replace(month=cursor.month + 1)
        month_end = min(next_month - timedelta(days=1), end)
        result.append((month_start.strftime("%Y-%m-%d"), month_end.strftime("%Y-%m-%d")))
        cursor = next_month
    return result


def current_month_range():
    today = date.today()
    first = today.replace(day=1)
    return first.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def fmt_dur(seconds):
    if seconds < 60:
        return f"{seconds:.1f}s"
    return f"{int(seconds // 60)}m {seconds % 60:04.1f}s"


def fmt_changes(changes):
    if not changes:
        return "không đổi"
    parts = []
    if changes.get("added"):   parts.append(f"+{changes['added']} mới")
    if changes.get("updated"): parts.append(f"~{changes['updated']} sửa")
    if changes.get("deleted"): parts.append(f"-{changes['deleted']} xóa")
    return ", ".join(parts) if parts else "không đổi"


class Timer:
    def __init__(self):
        self.elapsed = 0
    def __enter__(self):
        self._start = _time.time()
        return self
    def __exit__(self, *args):
        self.elapsed = round(_time.time() - self._start, 2)