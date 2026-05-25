"""
elt/extract/cns.py — Extract CNS Dược Sanfo (REST API → Bronze Parquet)
=========================================================================
Connection: get_ds('source.cns') → RestApiClient
Output:     get_ds('bronze.cns') → data/bronze/cns/{dim,fact}/

Usage:
    from elt.extract.cns import extract_cns_dims, extract_cns_cuoiky, extract_cns_facts

    results = extract_cns_dims()
    result, changed = extract_cns_cuoiky()
    results = extract_cns_facts(tu_ngay, den_ngay)
"""

import logging
import time as _time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

from elt.connections import get_ds, get_config
from .base import (
    ExtractResult, Timer, clean_df, table_hash,
    detect_changes, has_changes, fmt_changes, fmt_dur,
    load_checksums, save_checksums, update_checksum,
    write_parquet, read_parquet, ensure_dirs, months_between,
)

logger = logging.getLogger(__name__)

SOURCE = 'source.cns'
TARGET = 'bronze.cns'


# ═══════════════════════════════════════════════════════
# DIM REGISTRY
# ═══════════════════════════════════════════════════════

DIM_REGISTRY = [
    {"name": "DoiTuong",     "pk": "ID_DT",      "label": "Đối tượng"},
    {"name": "NguonLuc",     "pk": "ID_NL",      "label": "Sản phẩm"},
    {"name": "NhomDoiTuong", "pk": "ID_NHOM_DT", "label": "Nhóm ĐT"},
    {"name": "YeuToPhi",     "pk": "ID_YTP",     "label": "Nhân viên"},
]

FACT_REGISTRY = [
    {"name": "DonHangBanRa",  "label": "Đơn hàng bán ra", "extra_body": None},
    {"name": "CongNoSoLuong", "label": "Bảng kê chứng từ", "extra_body_key": "ma_tk"},
]


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════

def _api_to_df(data):
    """Convert API JSON response → DataFrame."""
    if isinstance(data, list) and data:
        return pd.json_normalize(data)
    elif isinstance(data, dict):
        return pd.DataFrame([data])
    return pd.DataFrame()


def _get_output_dir():
    return Path(get_ds(TARGET))


def _get_source_config():
    return get_config(SOURCE)


# ═══════════════════════════════════════════════════════
# EXTRACT: DIM
# ═══════════════════════════════════════════════════════

def extract_cns_dims():
    """Fetch tất cả dim tables. Returns list[ExtractResult]."""
    output_dir = _get_output_dir()
    dim_dir = output_dir / "dim"
    meta_dir = output_dir / "_meta"
    ensure_dirs(dim_dir, meta_dir)

    checksums = load_checksums(meta_dir)
    results = []
    today_str = date.today().isoformat()

    print(f"\n[CNS DIM] Extract {len(DIM_REGISTRY)} dim tables")

    try:
        client = get_ds(SOURCE)
        print(f"  Token... ✓")
    except Exception as e:
        print(f"  Token... ✗ {e}")
        return [ExtractResult(table='_token', status='error', error=str(e))]

    for dim in DIM_REGISTRY:
        name = dim['name']
        pk = dim['pk']
        print(f"  {dim['label']}...", end=" ", flush=True)

        with Timer() as t:
            try:
                data = client.get(name)
                df = clean_df(_api_to_df(data))
                df["_sync_date"] = today_str

                df_old = read_parquet(dim_dir / f"{name}.parquet")
                changes = detect_changes(df, df_old, pk)

                write_parquet(df, dim_dir / f"{name}.parquet")
                update_checksum(checksums, name, df, changes)

                results.append(ExtractResult(
                    table=name, layer='dim', rows=len(df),
                    seconds=t.elapsed, changes=changes,
                ))
                extra = f" ({fmt_changes(changes)})" if has_changes(changes) else ""
                print(f"✓ {len(df):,} dòng [{fmt_dur(t.elapsed)}]{extra}")

            except Exception as e:
                results.append(ExtractResult(
                    table=name, layer='dim', seconds=t.elapsed,
                    status='error', error=str(e),
                ))
                print(f"✗ {e} [{fmt_dur(t.elapsed)}]")

    save_checksums(meta_dir, checksums)
    return results


# ═══════════════════════════════════════════════════════
# EXTRACT: CUOI KY (SENSOR)
# ═══════════════════════════════════════════════════════

def extract_cns_cuoiky(den_ngay=None):
    """
    Fetch CuoiKyTaiKhoanCongNo — sensor detect thay đổi.
    Returns (ExtractResult, bool changed).
    """
    output_dir = _get_output_dir()
    fact_dir = output_dir / "fact"
    meta_dir = output_dir / "_meta"
    ensure_dirs(fact_dir, meta_dir)

    config = _get_source_config()
    den_ngay = den_ngay or date.today().strftime("%Y-%m-%d")
    ma_tk = config.get('ma_tk', '131')
    checksums = load_checksums(meta_dir)
    name = "CuoiKyTaiKhoanCongNo"

    print(f"\n[CNS SENSOR] CuoiKy đến {den_ngay}...", end=" ", flush=True)

    with Timer() as t:
        try:
            client = get_ds(SOURCE)
            data = client.post(name, {"DEN_NGAY": den_ngay, "MA_TK": ma_tk})
            df = clean_df(_api_to_df(data))
            df["_sync_date"] = date.today().isoformat()

            old_hash = checksums.get(name, {}).get("hash")
            new_hash = table_hash(df)
            changed = new_hash != old_hash

            write_parquet(df, fact_dir / f"{name}.parquet")
            update_checksum(checksums, name, df)
            save_checksums(meta_dir, checksums)

            result = ExtractResult(
                table=name, layer='fact', rows=len(df),
                seconds=t.elapsed, hash=new_hash,
            )
            print(f"✓ {len(df):,} dòng [{fmt_dur(t.elapsed)}] → {'CHANGED ⚡' if changed else 'không đổi'}")
            return result, changed

        except Exception as e:
            print(f"✗ {e} [{fmt_dur(t.elapsed)}]")
            return ExtractResult(
                table=name, layer='fact', seconds=t.elapsed,
                status='error', error=str(e),
            ), False


# ═══════════════════════════════════════════════════════
# EXTRACT: FACT (monthly chunks, timeout fallback)
# ═══════════════════════════════════════════════════════

def extract_cns_facts(tu_ngay, den_ngay, tables=None, incremental=False):
    """
    Fetch fact tables theo từng tháng.

    Args:
        tu_ngay, den_ngay: khoảng ngày fetch
        tables: list tên bảng (None = tất cả)
        incremental: True = chỉ fetch 4 tháng gần nhất,
                     merge với data cũ (giữ phần trước 4 tháng)

    Returns list[ExtractResult].
    """
    output_dir = _get_output_dir()
    fact_dir = output_dir / "fact"
    meta_dir = output_dir / "_meta"
    ensure_dirs(fact_dir, meta_dir)

    config = _get_source_config()
    ma_tk = config.get('ma_tk', '131')
    checksums = load_checksums(meta_dir)
    results = []
    today_str = date.today().isoformat()

    registry = FACT_REGISTRY
    if tables:
        table_set = set(tables)
        registry = [f for f in FACT_REGISTRY if f['name'] in table_set]

    # Incremental: tính lại tu_ngay = đầu tháng cách đây 3 tháng (tổng 4 tháng)
    if incremental:
        from dateutil.relativedelta import relativedelta
        end_dt = datetime.strptime(den_ngay, "%Y-%m-%d").date()
        inc_start = (end_dt - relativedelta(months=3)).replace(day=1)
        inc_tu_ngay = inc_start.strftime("%Y-%m-%d")
        print(f"[CNS FACT] Incremental mode: fetch {inc_tu_ngay} → {den_ngay} (4 tháng)")
    else:
        inc_tu_ngay = tu_ngay

    try:
        client = get_ds(SOURCE)
    except Exception as e:
        return [ExtractResult(table='_token', status='error', error=str(e))]

    for fact in registry:
        name = fact['name']
        extra_body = {}
        if fact.get('extra_body_key') == 'ma_tk':
            extra_body = {"MA_TK": ma_tk}

        result = _fetch_monthly(
            client, name, fact['label'], inc_tu_ngay, den_ngay,
            extra_body, fact_dir, checksums, today_str,
            incremental=incremental,
            inc_cutoff=inc_tu_ngay if incremental else None,
        )
        results.append(result)

    save_checksums(meta_dir, checksums)
    return results


def _fetch_monthly(client, name, label, tu_ngay, den_ngay,
                    extra_body, fact_dir, checksums, today_str,
                    incremental=False, inc_cutoff=None):
    """
    Fetch 1 fact table theo monthly chunks.

    incremental=True: sau khi fetch, merge với data cũ
      (giữ dòng có NGAY_CT < inc_cutoff, thay thế phần >= inc_cutoff).
    """
    month_ranges = months_between(tu_ngay, den_ngay)
    mode_label = "INCREMENTAL" if incremental else "FULL"
    print(f"\n[CNS FACT] {label} ({mode_label}): {len(month_ranges)} tháng [{tu_ngay} → {den_ngay}]")

    chunks = []
    detail = []
    t_total = _time.time()

    for m_start, m_end in month_ranges:
        print(f"  {m_start[:7]}  ({m_start} → {m_end})...", end=" ", flush=True)
        t0 = _time.time()

        try:
            body = {"TU_NGAY": m_start, "DEN_NGAY": m_end}
            body.update(extra_body)
            data = client.post(name, body)
            df = clean_df(_api_to_df(data))
            df["_sync_date"] = today_str
            elapsed = _time.time() - t0
            chunks.append(df)
            detail.append({"period": m_start[:7], "rows": len(df), "seconds": round(elapsed, 2)})
            print(f"{len(df):,} dòng [{fmt_dur(elapsed)}]")

        except requests.exceptions.ReadTimeout:
            elapsed = _time.time() - t0
            print(f"TIMEOUT [{fmt_dur(elapsed)}] → chia 10 ngày")
            sub_chunks, sub_detail = _fallback_10day(client, name, m_start, m_end, extra_body, today_str)
            chunks.extend(sub_chunks)
            sub_rows = sum(len(c) for c in sub_chunks)
            detail.append({"period": m_start[:7], "rows": sub_rows,
                           "seconds": round(sum(d["seconds"] for d in sub_detail), 2), "note": "fallback"})

        except Exception as e:
            elapsed = _time.time() - t0
            detail.append({"period": m_start[:7], "rows": 0, "seconds": round(elapsed, 2), "error": str(e)})
            print(f"✗ {e} [{fmt_dur(elapsed)}]")

    total_elapsed = round(_time.time() - t_total, 2)
    df_fetched = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()

    # Incremental: merge với data cũ
    if incremental and inc_cutoff and not df_fetched.empty:
        parquet_path = fact_dir / f"{name}.parquet"
        df_old = read_parquet(parquet_path)
        if df_old is not None and not df_old.empty:
            # Tìm cột ngày để cắt
            date_col = 'NGAY_CT' if 'NGAY_CT' in df_old.columns else None
            if date_col:
                df_old[date_col] = pd.to_datetime(df_old[date_col])
                df_fetched[date_col] = pd.to_datetime(df_fetched[date_col])
                cutoff_dt = pd.to_datetime(inc_cutoff)
                df_keep = df_old[df_old[date_col] < cutoff_dt]
                df_all = pd.concat([df_keep, df_fetched], ignore_index=True)
                print(f"  Merge: giữ {len(df_keep):,} cũ + {len(df_fetched):,} mới = {len(df_all):,}")
            else:
                df_all = df_fetched
        else:
            df_all = df_fetched
    else:
        df_all = df_fetched

    if not df_all.empty:
        write_parquet(df_all, fact_dir / f"{name}.parquet")
        update_checksum(checksums, name, df_all)

    print(f"  ── Tổng: {len(df_all):,} dòng [{fmt_dur(total_elapsed)}]")
    return ExtractResult(
        table=name, layer='fact', rows=len(df_all),
        seconds=total_elapsed, hash=checksums.get(name, {}).get('hash'),
        detail=detail,
    )


def _fallback_10day(client, name, m_start, m_end, extra_body, today_str):
    from datetime import datetime, timedelta
    sub_start = datetime.strptime(m_start, "%Y-%m-%d").date()
    sub_end = datetime.strptime(m_end, "%Y-%m-%d").date()
    chunks, detail = [], []
    cursor = sub_start
    while cursor <= sub_end:
        chunk_end = min(cursor + timedelta(days=9), sub_end)
        s, e = cursor.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")
        print(f"    {s} ~ {e}...", end=" ", flush=True)
        t0 = _time.time()
        try:
            body = {"TU_NGAY": s, "DEN_NGAY": e}
            body.update(extra_body)
            data = client.post(name, body)
            df = clean_df(_api_to_df(data))
            df["_sync_date"] = today_str
            elapsed = _time.time() - t0
            chunks.append(df)
            detail.append({"period": f"{s}~{e}", "rows": len(df), "seconds": round(elapsed, 2)})
            print(f"{len(df):,} [{fmt_dur(elapsed)}]")
        except Exception as ex:
            elapsed = _time.time() - t0
            detail.append({"period": f"{s}~{e}", "rows": 0, "seconds": round(elapsed, 2), "error": str(ex)})
            print(f"✗ {ex}")
        cursor = chunk_end + timedelta(days=1)
    return chunks, detail


# ═══════════════════════════════════════════════════════
# CONVENIENCE
# ═══════════════════════════════════════════════════════

def extract_cns_all(tu_ngay=None, den_ngay=None, incremental=False):
    """
    Extract tất cả CNS (dims + cuoiky + facts).

    Args:
        incremental: True = facts chỉ fetch 4 tháng gần nhất

    Returns (list[ExtractResult], bool cuoiky_changed).
    """
    config = _get_source_config()
    tu_ngay = tu_ngay or config.get('start_date', '2024-01-01')
    den_ngay = den_ngay or date.today().strftime("%Y-%m-%d")

    all_results = []
    all_results.extend(extract_cns_dims())

    cuoiky_result, changed = extract_cns_cuoiky(den_ngay)
    all_results.append(cuoiky_result)

    all_results.extend(extract_cns_facts(tu_ngay, den_ngay, incremental=incremental))
    return all_results, changed