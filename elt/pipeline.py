"""
elt/pipeline.py — Pipeline orchestrator
=========================================
Kết nối extract → transform thành 1 flow.

Usage:
    from elt.pipeline import run_pipeline
    results = run_pipeline()                          # full extract + transform
    results = run_pipeline(skip_extract=True)         # chỉ transform
    results = run_pipeline(cns_incremental=True)      # CNS chỉ 4 tháng gần nhất
    results = run_pipeline(skip_cns=True)             # bỏ qua CNS
"""

import logging
import time as _time
from datetime import datetime, date

from elt.extract.asia import extract_asia
from elt.extract.cns import extract_cns_dims, extract_cns_cuoiky, extract_cns_facts
from elt.transform.base import run_transforms
from elt.connections import get_config

logger = logging.getLogger(__name__)


def run_pipeline(skip_extract=False, skip_transform=False, tables=None,
                 skip_cns=False, cns_incremental=True, cns_full=False):
    """
    Chạy full pipeline: extract asia + cns → transform → silver.

    Args:
        skip_extract:     bỏ qua extract (chỉ chạy transform)
        skip_transform:   bỏ qua transform (chỉ chạy extract)
        tables:           list tên bảng (None = tất cả)
        skip_cns:         bỏ qua CNS extract
        cns_incremental:  CNS facts chỉ fetch 4 tháng gần nhất (default True)
        cns_full:         CNS facts fetch toàn bộ (override incremental)

    Returns:
        dict {
            'extract_asia': list[ExtractResult],
            'extract_cns': list[ExtractResult],
            'transform': list[TransformResult],
            'seconds': float,
            'status': 'ok' | 'partial' | 'error',
            'timestamp': str,
        }
    """
    t0 = _time.time()
    result = {
        'extract_asia': [],
        'extract_cns': [],
        'transform': [],
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
    }

    # ── EXTRACT ASIA ──
    if not skip_extract:
        print("\n" + "=" * 60)
        print("  EXTRACT — AsiaSoft (SQL Server)")
        print("=" * 60)

        try:
            asia_results = extract_asia(tables=tables)
            result['extract_asia'] = asia_results

            errors = [r for r in asia_results if r.status == 'error'
                       and not r.table.startswith('_') and not r.optional]
            if errors:
                logger.error(f"[Pipeline] Asia extract failed: {len(errors)} required table errors")
                result['status'] = 'error'
                result['seconds'] = round(_time.time() - t0, 2)
                return result

        except Exception as e:
            logger.error(f"[Pipeline] Asia extract exception: {e}")
            result['status'] = 'error'
            result['seconds'] = round(_time.time() - t0, 2)
            return result

    # ── EXTRACT CNS ──
    if not skip_extract and not skip_cns:
        print("\n" + "=" * 60)
        print("  EXTRACT — Dược Sanfo (CNS API)")
        print("=" * 60)

        cns_results = []
        try:
            # 1. Dims (luôn full — nhẹ)
            cns_results.extend(extract_cns_dims())

            # 2. CuoiKy sensor
            cuoiky_result, cuoiky_changed = extract_cns_cuoiky()
            cns_results.append(cuoiky_result)

            # 3. Facts
            config = get_config('source.cns')
            tu_ngay = config.get('start_date', '2024-01-01')
            den_ngay = date.today().strftime("%Y-%m-%d")

            incremental = cns_incremental and not cns_full
            cns_results.extend(
                extract_cns_facts(tu_ngay, den_ngay, incremental=incremental)
            )

            result['extract_cns'] = cns_results

            # CNS errors không block pipeline (non-critical)
            cns_errors = [r for r in cns_results if r.status == 'error'
                          and not r.table.startswith('_')]
            if cns_errors:
                logger.warning(f"[Pipeline] CNS extract: {len(cns_errors)} errors (non-blocking)")
                result['status'] = 'partial'

        except Exception as e:
            logger.warning(f"[Pipeline] CNS extract exception (non-blocking): {e}")
            result['status'] = 'partial'

    # ── TRANSFORM ──
    if not skip_transform:
        print("\n" + "=" * 60)
        print("  TRANSFORM → Silver (Delta Lake)")
        print("=" * 60)

        try:
            transform_results = run_transforms(names=tables)
            result['transform'] = transform_results

            errors = [r for r in transform_results if r.status == 'error']
            if errors:
                result['status'] = 'partial'

        except Exception as e:
            logger.error(f"[Pipeline] Transform exception: {e}")
            result['status'] = 'partial'

    result['seconds'] = round(_time.time() - t0, 2)

    # Summary
    asia_ok = sum(1 for r in result['extract_asia'] if r.status == 'ok')
    cns_ok = sum(1 for r in result['extract_cns'] if r.status == 'ok')
    tr_ok = sum(1 for r in result['transform'] if r.status == 'ok')
    print(f"\n{'=' * 60}")
    print(f"  PIPELINE {'✓' if result['status'] == 'ok' else '⚠'} "
          f"Asia: {asia_ok}, CNS: {cns_ok}, Transform: {tr_ok} OK, "
          f"Total: {result['seconds']:.1f}s")
    print(f"{'=' * 60}")

    return result