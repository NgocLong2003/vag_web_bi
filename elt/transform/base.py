"""
elt/transform/base.py — Base transform: Bronze Parquet → Silver Delta Lake
============================================================================
Cung cấp:
  - write_delta():     ghi DataFrame/Table vào Delta table (overwrite)
  - read_bronze():     đọc Parquet từ bronze
  - Transform:         base class cho merge transforms (asia + cns)
  - CopyTransform:     copy thẳng 1 bảng bronze → silver (không merge)
  - TransformResult:   dataclass kết quả
  - run_transforms():  chạy tất cả transforms đã đăng ký

Silver output:
    data/silver/
      PTHUBAOCO/
        part-00000-xxx.parquet
        _delta_log/
          00000000000000000000.json
          00000000000000000001.json
      BKHDBANHANG/
        ...

DuckDB đọc silver qua:
    dt = DeltaTable('data/silver/PTHUBAOCO')
    files = dt.file_uris()
    SELECT * FROM read_parquet([file1, file2, ...])
"""

import logging
import time as _time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from deltalake import write_deltalake, DeltaTable

from elt.connections import get_ds

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# RESULT
# ═══════════════════════════════════════════════════════

@dataclass
class TransformResult:
    table: str
    rows: int = 0
    seconds: float = 0
    status: str = 'ok'         # 'ok', 'error', 'skipped'
    error: Optional[str] = None
    version: Optional[int] = None


# ═══════════════════════════════════════════════════════
# DELTA LAKE I/O
# ═══════════════════════════════════════════════════════

def write_delta(table_path, df, mode='overwrite'):
    """
    Ghi DataFrame → Delta Lake table.

    Args:
        table_path: str/Path đến thư mục Delta (vd: 'data/silver/PTHUBAOCO')
        df:         pandas DataFrame hoặc pyarrow Table
        mode:       'overwrite' (replace) hoặc 'append'

    Returns:
        int version number
    """
    table_path = str(table_path)

    if isinstance(df, pd.DataFrame):
        pa_table = pa.Table.from_pandas(df, preserve_index=False)
    elif isinstance(df, pa.Table):
        pa_table = df
    else:
        raise TypeError(f"Expected DataFrame or pyarrow Table, got {type(df)}")

    if len(pa_table) == 0:
        logger.warning(f"[Transform] {table_path}: empty table, skipping")
        return -1

    write_deltalake(table_path, pa_table, mode=mode)

    dt = DeltaTable(table_path)
    return dt.version()


def read_bronze(bronze_ds, layer, table_name):
    """
    Đọc 1 bảng từ bronze Parquet.

    Args:
        bronze_ds:  datasource name (vd: 'bronze.asia')
        layer:      'dim' hoặc 'fact'
        table_name: tên bảng (vd: 'PTHUBAOCO')

    Returns:
        pandas DataFrame hoặc None nếu file không tồn tại
    """
    data_dir = Path(get_ds(bronze_ds))
    path = data_dir / layer / f"{table_name}.parquet"
    if not path.exists():
        logger.warning(f"[Transform] Bronze file not found: {path}")
        return None
    return pd.read_parquet(path)


def silver_path(table_name):
    """Trả về path đến silver Delta table."""
    silver_dir = Path(get_ds('silver'))
    return silver_dir / table_name


# ═══════════════════════════════════════════════════════
# BASE CLASSES
# ═══════════════════════════════════════════════════════

class Transform:
    """
    Base class cho merge transforms.
    Override run() để implement logic.
    """
    name: str = ''

    def run(self) -> TransformResult:
        raise NotImplementedError


class CopyTransform(Transform):
    """
    Copy 1 bảng từ bronze.asia → silver (không merge, không transform).
    Dùng cho bảng chỉ có ở AsiaSoft, chưa cần merge CNS.
    """
    def __init__(self, name, layer='fact', bronze_ds='bronze.asia'):
        self.name = name
        self.layer = layer
        self.bronze_ds = bronze_ds

    def run(self) -> TransformResult:
        t0 = _time.time()
        try:
            df = read_bronze(self.bronze_ds, self.layer, self.name)
            if df is None:
                return TransformResult(
                    table=self.name, status='skipped',
                    seconds=round(_time.time() - t0, 2),
                    error=f"Bronze file not found",
                )

            out = silver_path(self.name)
            version = write_delta(out, df)
            elapsed = round(_time.time() - t0, 2)

            return TransformResult(
                table=self.name, rows=len(df),
                seconds=elapsed, version=version,
            )
        except Exception as e:
            return TransformResult(
                table=self.name, status='error',
                seconds=round(_time.time() - t0, 2),
                error=str(e),
            )


# ═══════════════════════════════════════════════════════
# TRANSFORM REGISTRY & RUNNER
# ═══════════════════════════════════════════════════════

# Registry: list Transform instances
# Mỗi transform file register vào đây
TRANSFORMS = []


def register(transform):
    """Đăng ký 1 transform vào registry."""
    TRANSFORMS.append(transform)
    return transform


def run_transforms(names=None):
    """
    Chạy tất cả (hoặc selected) transforms.

    Args:
        names: list tên bảng cần chạy (None = tất cả)

    Returns:
        list[TransformResult]
    """
    # Import tất cả transform modules để trigger registration
    _load_all_transforms()

    transforms = TRANSFORMS
    if names:
        name_set = set(names)
        transforms = [t for t in TRANSFORMS if t.name in name_set]

    results = []
    total_t0 = _time.time()

    print(f"\n[TRANSFORM] Chạy {len(transforms)} transforms → silver (Delta Lake)")

    for t in transforms:
        print(f"  {t.name}...", end=" ", flush=True)
        result = t.run()
        results.append(result)

        if result.status == 'ok':
            v = f" (v{result.version})" if result.version is not None else ""
            print(f"✓ {result.rows:,} dòng [{result.seconds:.1f}s]{v}")
        elif result.status == 'skipped':
            print(f"⊘ skipped: {result.error}")
        else:
            print(f"✗ {result.error}")

    total = round(_time.time() - total_t0, 2)
    ok = sum(1 for r in results if r.status == 'ok')
    err = sum(1 for r in results if r.status == 'error')
    skip = sum(1 for r in results if r.status == 'skipped')
    rows = sum(r.rows for r in results)
    print(f"  ── Tổng: {ok} OK, {skip} skipped, {err} lỗi, {rows:,} dòng [{total:.1f}s]")

    return results


def _load_all_transforms():
    """Import tất cả modules trong elt/transform/ để trigger register()."""
    import importlib
    import pkgutil
    import elt.transform as pkg

    for importer, modname, ispkg in pkgutil.iter_modules(pkg.__path__):
        if modname != 'base':
            importlib.import_module(f'elt.transform.{modname}')