"""
Sanfo Bronze Fetcher
=====================
Fetch data từ API Dược SanFo → lưu Parquet (bronze layer).

2 chế độ chạy:
    python sanfo_fetch_bronze.py --mode monthly    ← mỗi 30 phút (nhẹ, theo tháng)
    python sanfo_fetch_bronze.py --mode daily      ← mỗi ngày (chi tiết, theo ngày)
    python sanfo_fetch_bronze.py --mode full        ← chạy cả 2 + dim (lần đầu)

Output:
    data/bronze/sanfo/
      dim/DoiTuong.parquet, NguonLuc.parquet, NhomDoiTuong.parquet, YeuToPhi.parquet
      fact/DonHangBanRa_monthly.parquet       ← từ 2024, group by tháng
      fact/DonHangBanRa_daily.parquet         ← 6 tháng gần nhất, từng ngày
      fact/CongNoSoLuong_monthly.parquet      ← từ 2024, group by tháng
      fact/CongNoSoLuong_daily.parquet        ← 6 tháng gần nhất, từng ngày
      fact/CuoiKyTaiKhoanCongNo.parquet       ← snapshot
      _meta/sync_state.json

Yêu cầu:
    pip install requests pandas pyarrow
"""

import requests
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import argparse
import sys
import re
import os
import json
import time as _time
from datetime import datetime, timedelta, date
from pathlib import Path

# ============================================================
# CẤU HÌNH
# ============================================================
BASE_URL = "http://113.190.242.246:8086"
AUTH_URL = f"{BASE_URL}/auth/token"
API_URL  = f"{BASE_URL}/api"

CREDENTIALS = {
    "grant_type": "password",
    "username": "admin",
    "password": "CNS@Vietnam.2009",
    "client_id": "bc989378a62549e9a918df74b59d3f36",
}

SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT = SCRIPT_DIR / "data" / "bronze" / "sanfo"

_ILLEGAL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


# ============================================================
# UTILITIES
# ============================================================
def clean_df(df):
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(
            lambda x: _ILLEGAL_CHARS_RE.sub('', x) if isinstance(x, str) else x
        )
    return df


def fmt_dur(s):
    if s < 60:
        return f"{s:.1f}s"
    return f"{int(s // 60)}m {s % 60:04.1f}s"


def write_parquet(df, path):
    """Ghi DataFrame → Parquet (snappy compression)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, str(path), compression='snappy')


def months_between(start_str, end_str):
    """Trả về list (first_day, last_day) cho mỗi tháng trong range."""
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_str, "%Y-%m-%d").date()
    result = []
    cursor = start.replace(day=1)
    while cursor <= end:
        month_start = max(cursor, start)
        # Last day of this month
        if cursor.month == 12:
            next_month = cursor.replace(year=cursor.year + 1, month=1)
        else:
            next_month = cursor.replace(month=cursor.month + 1)
        month_end = min(next_month - timedelta(days=1), end)
        result.append((month_start.strftime("%Y-%m-%d"), month_end.strftime("%Y-%m-%d")))
        cursor = next_month
    return result


def days_between(start_str, end_str):
    """Trả về list ngày (YYYY-MM-DD) trong range."""
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_str, "%Y-%m-%d").date()
    result = []
    cursor = start
    while cursor <= end:
        result.append(cursor.strftime("%Y-%m-%d"))
        cursor += timedelta(days=1)
    return result


# ============================================================
# API
# ============================================================
_token_cache = {"token": None, "expires": 0}


def get_token():
    now = _time.time()
    if _token_cache["token"] and now < _token_cache["expires"]:
        return _token_cache["token"]
    print("  Token...", end=" ", flush=True)
    resp = requests.post(AUTH_URL, data=CREDENTIALS, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }, timeout=30)
    resp.raise_for_status()
    token = resp.json()["access_token"]
    _token_cache["token"] = token
    _token_cache["expires"] = now + 3500
    print("✓")
    return token


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}


def api_get(token, endpoint):
    resp = requests.get(f"{API_URL}/{endpoint}", headers=_headers(token), timeout=300)
    resp.raise_for_status()
    data = resp.json()
    return pd.json_normalize(data) if data else pd.DataFrame()


def api_post(token, endpoint, body):
    resp = requests.post(f"{API_URL}/{endpoint}", json=body, headers=_headers(token), timeout=300)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return pd.json_normalize(data) if data else pd.DataFrame()
    elif isinstance(data, dict):
        return pd.DataFrame([data])
    return pd.DataFrame()


# ============================================================
# FETCH: DIM TABLES
# ============================================================
def fetch_dims(token, output_dir, benchmark):
    print("\n[DIM TABLES]")
    dim_dir = output_dir / "dim"
    today_str = date.today().isoformat()

    for endpoint, label in [
        ("DoiTuong", "Đối tượng"),
        ("NguonLuc", "Sản phẩm"),
        ("NhomDoiTuong", "Nhóm ĐT"),
        ("YeuToPhi", "Nhân viên"),
    ]:
        print(f"  {label}...", end=" ", flush=True)
        t0 = _time.time()
        try:
            df = clean_df(api_get(token, endpoint))
            df["_sync_date"] = today_str
            elapsed = _time.time() - t0
            write_parquet(df, dim_dir / f"{endpoint}.parquet")
            print(f"✓ {len(df):,} dòng [{fmt_dur(elapsed)}]")
            benchmark.append({"step": f"dim/{endpoint}", "rows": len(df), "seconds": round(elapsed, 2)})
        except Exception as e:
            elapsed = _time.time() - t0
            print(f"✗ {e} [{fmt_dur(elapsed)}]")
            benchmark.append({"step": f"dim/{endpoint}", "rows": 0, "seconds": round(elapsed, 2), "error": str(e)})


# ============================================================
# FETCH: CUOI KY TAI KHOAN CONG NO
# ============================================================
def fetch_cuoiky(token, den_ngay, ma_tk, output_dir, benchmark):
    print("\n[CUỐI KỲ TÀI KHOẢN CÔNG NỢ]")
    print(f"  Đến ngày: {den_ngay}...", end=" ", flush=True)
    t0 = _time.time()
    try:
        df = clean_df(api_post(token, "CuoiKyTaiKhoanCongNo", {
            "DEN_NGAY": den_ngay, "MA_TK": ma_tk
        }))
        df["_sync_date"] = date.today().isoformat()
        elapsed = _time.time() - t0
        write_parquet(df, output_dir / "fact" / "CuoiKyTaiKhoanCongNo.parquet")
        print(f"✓ {len(df):,} dòng [{fmt_dur(elapsed)}]")
        benchmark.append({"step": "fact/CuoiKyTaiKhoanCongNo", "rows": len(df), "seconds": round(elapsed, 2)})
    except Exception as e:
        elapsed = _time.time() - t0
        print(f"✗ {e} [{fmt_dur(elapsed)}]")
        benchmark.append({"step": "fact/CuoiKyTaiKhoanCongNo", "rows": 0, "seconds": round(elapsed, 2), "error": str(e)})


# ============================================================
# FETCH: FACT MONTHLY (theo tháng)
# ============================================================
def fetch_fact_monthly(token, endpoint, tu_ngay, den_ngay, extra_body, label, output_path, benchmark):
    """Fetch fact table theo từng tháng. Nếu timeout → fallback chia 10 ngày."""
    print(f"\n[{label} — MONTHLY]")
    month_ranges = months_between(tu_ngay, den_ngay)
    print(f"  {len(month_ranges)} tháng [{tu_ngay} → {den_ngay}]")

    chunks = []
    timings = []
    t_total = _time.time()
    today_str = date.today().isoformat()

    for m_start, m_end in month_ranges:
        print(f"  {m_start[:7]}  ({m_start} → {m_end})...", end=" ", flush=True)
        t0 = _time.time()
        try:
            body = {"TU_NGAY": m_start, "DEN_NGAY": m_end}
            if extra_body:
                body.update(extra_body)
            df = clean_df(api_post(token, endpoint, body))
            df["_sync_date"] = today_str
            elapsed = _time.time() - t0
            chunks.append(df)
            timings.append({"period": m_start[:7], "rows": len(df), "seconds": round(elapsed, 2)})
            print(f"{len(df):,} dòng [{fmt_dur(elapsed)}]")

        except requests.exceptions.ReadTimeout:
            elapsed = _time.time() - t0
            print(f"TIMEOUT [{fmt_dur(elapsed)}] → chia nhỏ 10 ngày")
            # Fallback: chia thành chunks 10 ngày
            sub_start = datetime.strptime(m_start, "%Y-%m-%d").date()
            sub_end = datetime.strptime(m_end, "%Y-%m-%d").date()
            sub_rows = 0
            sub_t0 = _time.time()
            cursor = sub_start
            while cursor <= sub_end:
                chunk_end = min(cursor + timedelta(days=9), sub_end)
                s, e = cursor.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")
                print(f"    {s} ~ {e}...", end=" ", flush=True)
                t1 = _time.time()
                try:
                    body = {"TU_NGAY": s, "DEN_NGAY": e}
                    if extra_body:
                        body.update(extra_body)
                    df_sub = clean_df(api_post(token, endpoint, body))
                    df_sub["_sync_date"] = today_str
                    chunks.append(df_sub)
                    sub_rows += len(df_sub)
                    print(f"{len(df_sub):,} [{fmt_dur(_time.time() - t1)}]")
                except Exception as e2:
                    print(f"✗ {e2}")
                cursor = chunk_end + timedelta(days=1)
            sub_elapsed = _time.time() - sub_t0
            timings.append({"period": m_start[:7], "rows": sub_rows, "seconds": round(sub_elapsed, 2), "note": "fallback 10d"})

        except Exception as e:
            elapsed = _time.time() - t0
            timings.append({"period": m_start[:7], "rows": 0, "seconds": round(elapsed, 2), "error": str(e)})
            print(f"✗ {e} [{fmt_dur(elapsed)}]")

    total_elapsed = _time.time() - t_total
    df_all = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    total_rows = len(df_all)

    if not df_all.empty:
        write_parquet(df_all, output_path)

    print(f"  ── Tổng: {total_rows:,} dòng [{fmt_dur(total_elapsed)}]")
    benchmark.append({
        "step": f"fact/{endpoint}_monthly",
        "rows": total_rows,
        "seconds": round(total_elapsed, 2),
        "detail": timings,
    })
    return df_all


# ============================================================
# FETCH: FACT DAILY (từng ngày)
# ============================================================
def fetch_fact_daily(token, endpoint, tu_ngay, den_ngay, extra_body, label, output_path, benchmark):
    """Fetch fact table từng ngày một."""
    print(f"\n[{label} — DAILY]")
    day_list = days_between(tu_ngay, den_ngay)
    print(f"  {len(day_list)} ngày [{tu_ngay} → {den_ngay}]")

    chunks = []
    timings = []
    t_total = _time.time()
    today_str = date.today().isoformat()

    for day_str in day_list:
        print(f"    {day_str}...", end=" ", flush=True)
        t0 = _time.time()
        try:
            body = {"TU_NGAY": day_str, "DEN_NGAY": day_str}
            if extra_body:
                body.update(extra_body)
            df = clean_df(api_post(token, endpoint, body))
            df["_sync_date"] = today_str
            elapsed = _time.time() - t0
            chunks.append(df)
            timings.append({"ngay": day_str, "rows": len(df), "seconds": round(elapsed, 2)})
            print(f"{len(df):,} dòng [{fmt_dur(elapsed)}]")
        except Exception as e:
            elapsed = _time.time() - t0
            timings.append({"ngay": day_str, "rows": 0, "seconds": round(elapsed, 2), "error": str(e)})
            print(f"✗ {e} [{fmt_dur(elapsed)}]")

    total_elapsed = _time.time() - t_total
    df_all = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    total_rows = len(df_all)

    if not df_all.empty:
        write_parquet(df_all, output_path)

    print(f"  ── Tổng: {total_rows:,} dòng, {len(day_list)} ngày [{fmt_dur(total_elapsed)}]")
    benchmark.append({
        "step": f"fact/{endpoint}_daily",
        "rows": total_rows,
        "seconds": round(total_elapsed, 2),
        "days": len(day_list),
        "detail": timings,
    })
    return df_all


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Sanfo Bronze Fetcher")
    parser.add_argument("--mode", choices=["monthly", "daily", "full"], default="full",
                        help="monthly=30min update, daily=chi tiết, full=tất cả")
    parser.add_argument("--tu-ngay-monthly", default="2024-01-01",
                        help="Ngày bắt đầu cho monthly (mặc định: 2024-01-01)")
    parser.add_argument("--daily-months", type=int, default=6,
                        help="Số tháng gần nhất cho daily (mặc định: 6)")
    parser.add_argument("--den-ngay", default=None,
                        help="Ngày kết thúc (mặc định: hôm nay)")
    parser.add_argument("--ma-tk", default="131")
    parser.add_argument("--output", default=None,
                        help="Thư mục output (mặc định: data/bronze/sanfo/)")
    args = parser.parse_args()

    today = date.today()
    den_ngay = args.den_ngay or today.strftime("%Y-%m-%d")
    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT

    # Tính ngày bắt đầu cho daily (6 tháng trước)
    daily_start = today.replace(day=1)
    for _ in range(args.daily_months):
        daily_start = (daily_start - timedelta(days=1)).replace(day=1)
    tu_ngay_daily = daily_start.strftime("%Y-%m-%d")

    # Tạo thư mục
    (output_dir / "dim").mkdir(parents=True, exist_ok=True)
    (output_dir / "fact").mkdir(parents=True, exist_ok=True)
    (output_dir / "_meta").mkdir(parents=True, exist_ok=True)

    mode = args.mode
    print("=" * 64)
    print(f"  SANFO BRONZE FETCHER — {mode.upper()}")
    print("=" * 64)
    print(f"  Output         : {output_dir}")
    if mode in ("monthly", "full"):
        print(f"  Monthly range  : {args.tu_ngay_monthly} → {den_ngay}")
    if mode in ("daily", "full"):
        print(f"  Daily range    : {tu_ngay_daily} → {den_ngay}")
    print(f"  MA_TK          : {args.ma_tk}")
    print("=" * 64)

    t_grand = _time.time()
    benchmark = []
    token = get_token()

    extra_cnsl = {"MA_TK": args.ma_tk}

    # ── DIM (chạy mọi mode — nhẹ, ~15s, đảm bảo fact luôn dùng dim mới nhất) ──
    fetch_dims(token, output_dir, benchmark)

    # ── CUỐI KỲ (chạy mọi mode) ──
    fetch_cuoiky(token, den_ngay, args.ma_tk, output_dir, benchmark)

    # ── MONTHLY FACTS ──
    if mode in ("monthly", "full"):
        fetch_fact_monthly(
            token, "DonHangBanRa",
            args.tu_ngay_monthly, den_ngay, None,
            "ĐƠN HÀNG BÁN RA",
            output_dir / "fact" / "DonHangBanRa_monthly.parquet",
            benchmark,
        )
        fetch_fact_monthly(
            token, "CongNoSoLuong",
            args.tu_ngay_monthly, den_ngay, extra_cnsl,
            "BẢNG KÊ CHỨNG TỪ",
            output_dir / "fact" / "CongNoSoLuong_monthly.parquet",
            benchmark,
        )

    # ── DAILY FACTS ──
    if mode in ("daily", "full"):
        fetch_fact_daily(
            token, "DonHangBanRa",
            tu_ngay_daily, den_ngay, None,
            "ĐƠN HÀNG BÁN RA",
            output_dir / "fact" / "DonHangBanRa_daily.parquet",
            benchmark,
        )
        fetch_fact_daily(
            token, "CongNoSoLuong",
            tu_ngay_daily, den_ngay, extra_cnsl,
            "BẢNG KÊ CHỨNG TỪ",
            output_dir / "fact" / "CongNoSoLuong_daily.parquet",
            benchmark,
        )

    grand_total = _time.time() - t_grand

    # ── GHI SYNC STATE ──
    sync_state = {
        "mode": mode,
        "completed_at": datetime.now().isoformat(),
        "grand_total_seconds": round(grand_total, 2),
        "den_ngay": den_ngay,
        "steps": benchmark,
    }
    if mode in ("monthly", "full"):
        sync_state["monthly_range"] = {"tu_ngay": args.tu_ngay_monthly, "den_ngay": den_ngay}
    if mode in ("daily", "full"):
        sync_state["daily_range"] = {"tu_ngay": tu_ngay_daily, "den_ngay": den_ngay}

    state_path = output_dir / "_meta" / "sync_state.json"
    # Merge với state cũ (giữ history)
    old_state = {}
    if state_path.exists():
        try:
            with open(state_path) as f:
                old_state = json.load(f)
        except:
            pass

    old_state[f"last_{mode}"] = sync_state
    old_state["last_any"] = {
        "mode": mode,
        "completed_at": sync_state["completed_at"],
        "grand_total_seconds": sync_state["grand_total_seconds"],
    }

    with open(state_path, "w") as f:
        json.dump(old_state, f, indent=2, ensure_ascii=False, default=str)

    # ── SUMMARY ──
    print(f"\n{'=' * 64}")
    print(f"  ✓ HOÀN TẤT — {mode.upper()}")
    print()

    # List output files
    print(f"  ┌─ OUTPUT FILES ─────────────────────────────────┐")
    for root, dirs, files in os.walk(output_dir):
        for f in sorted(files):
            if f.endswith('.parquet'):
                fp = Path(root) / f
                size_mb = fp.stat().st_size / 1024 / 1024
                rel = fp.relative_to(output_dir)
                print(f"  │ {str(rel):<40} {size_mb:>6.1f} MB │")
    print(f"  ├─ BENCHMARK ─────────────────────────────────────┤")

    for b in benchmark:
        step = b["step"]
        rows = b["rows"]
        secs = b["seconds"]
        extra = ""
        if b.get("days"):
            extra = f" ({b['days']} ngày)"
        elif b.get("detail"):
            n = len(b["detail"])
            extra = f" ({n} chunks)"
        if b.get("error"):
            extra += f" ✗ {b['error'][:30]}"
        print(f"  │ {step:<30} {rows:>8,} dòng  {fmt_dur(secs):>8}{extra}")

    print(f"  ├─────────────────────────────────────────────────┤")
    print(f"  │ TỔNG:  {fmt_dur(grand_total):>10}                               │")
    print(f"  └─────────────────────────────────────────────────┘")
    print(f"{'=' * 64}")


if __name__ == "__main__":
    main()