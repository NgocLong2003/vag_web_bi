"""
elt/transform/bkhdbanhang.py — Merge BKHDBANHANG: Asia + CNS doanh số
=======================================================================
Asia:  bronze.asia/fact/BKHDBANHANG.parquet  (giữ nguyên)
CNS:   bronze.cns/fact/CongNoSoLuong.parquet
       → WHERE MA_LOAI_CT = 'HHA'
       → GROUP BY ngày → SUM(PS_NO - PS_CO) = tien_nt2
       → gắn cố định ma_kh='TPBVSK', ma_bp='TN', ...
Output: silver/BKHDBANHANG (Delta Lake) = UNION(asia, cns_agg)
"""

import logging
import time as _time

import pandas as pd

from .base import (
    Transform, TransformResult,
    read_bronze, write_delta, silver_path, register,
)

logger = logging.getLogger(__name__)


def _build_cns_doanhso(df_cnsl):
    """
    Aggregate CongNoSoLuong → doanh số theo ngày, schema BKHDBANHANG.

    Input:  df_cnsl (full CongNoSoLuong bronze)
    Output: DataFrame schema giống BKHDBANHANG_VIEW
    """
    if df_cnsl is None or df_cnsl.empty:
        return pd.DataFrame()

    # Filter loại chứng từ doanh số
    mask = df_cnsl['MA_LOAI_CT'] == 'HHA'
    df = df_cnsl[mask].copy()
    if df.empty:
        return pd.DataFrame()

    # Parse ngày
    df['_ngay'] = pd.to_datetime(df['NGAY_CT']).dt.date

    # Group by ngày — gộp tất cả đối tượng
    grp = df.groupby('_ngay', as_index=False).agg(
        ps_no=('PS_NO', 'sum'),
        ps_co=('PS_CO', 'sum'),
    )

    # Doanh số = PS_NO - PS_CO (theo logic nghiệp vụ đã xác nhận)
    grp['tien_nt2'] = grp['ps_no'] - grp['ps_co']

    # Build output theo schema BKHDBANHANG_VIEW
    out = pd.DataFrame({
        'ngay_ct': pd.to_datetime(grp['_ngay']),
        'ma_kh': 'TPBVSK',
        'ma_vt': 'TPBVSK',
        'ten_vt': 'TPBVSK',
        'dvt': '',
        'ma_bp': 'TN',
        'ma_nvkd': 'TPBVSK',
        'ma_kho': '',
        'so_luong': 0.0,
        'gia_nt2': 0.0,
        'tien_nt2': grp['tien_nt2'].values,
        'tien_ck_nt': 0.0,
        'ts_gtgt': 0.0,
        'thue_gtgt_nt': 0.0,
    })

    return out


class BkhdBanHangTransform(Transform):
    name = 'BKHDBANHANG'

    def run(self) -> TransformResult:
        t0 = _time.time()
        try:
            # 1. Đọc Asia bronze
            df_asia = read_bronze('bronze.asia', 'fact', 'BKHDBANHANG')
            if df_asia is None:
                return TransformResult(
                    table=self.name, status='error',
                    seconds=round(_time.time() - t0, 2),
                    error='Asia BKHDBANHANG not found',
                )

            # 2. Đọc CNS bronze (có thể chưa có)
            df_cnsl = read_bronze('bronze.cns', 'fact', 'CongNoSoLuong')
            df_cns = _build_cns_doanhso(df_cnsl)

            # 3. UNION
            if not df_cns.empty:
                if 'ngay_ct' in df_asia.columns:
                    df_asia['ngay_ct'] = pd.to_datetime(df_asia['ngay_ct'])
                # Ép dtype số cho asia (tránh object mixed int/float)
                num_cols = ['so_luong', 'gia_nt2', 'tien_nt2', 'tien_ck_nt',
                            'ts_gtgt', 'thue_gtgt_nt']
                for col in num_cols:
                    if col in df_asia.columns:
                        df_asia[col] = pd.to_numeric(df_asia[col], errors='coerce').fillna(0)
                df_merged = pd.concat([df_asia, df_cns], ignore_index=True)
                cns_rows = len(df_cns)
            else:
                df_merged = df_asia
                cns_rows = 0

            # 4. Ghi silver
            out = silver_path(self.name)
            version = write_delta(out, df_merged)
            elapsed = round(_time.time() - t0, 2)

            logger.info(f"[Transform] BKHDBANHANG: asia={len(df_asia)}, cns={cns_rows}, total={len(df_merged)}")

            return TransformResult(
                table=self.name, rows=len(df_merged),
                seconds=elapsed, version=version,
            )

        except Exception as e:
            return TransformResult(
                table=self.name, status='error',
                seconds=round(_time.time() - t0, 2),
                error=str(e),
            )


register(BkhdBanHangTransform())