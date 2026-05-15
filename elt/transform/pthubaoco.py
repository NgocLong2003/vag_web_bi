"""
elt/transform/pthubaoco.py — Merge PTHUBAOCO: Asia + CNS doanh thu
====================================================================
Asia:  bronze.asia/fact/PTHUBAOCO.parquet  (giữ nguyên)
CNS:   bronze.cns/fact/CongNoSoLuong.parquet
       → WHERE MA_LOAI_CT IN ('PTT', 'CNT')
       → GROUP BY ngày → SUM(PS_CO - PS_NO) = ps_co
       → gắn cố định ma_kh_ct='TPBVSK', ma_bp='TN', ...
Output: silver/PTHUBAOCO (Delta Lake) = UNION(asia, cns_agg)
"""

import logging
import time as _time

import pandas as pd

from .base import (
    Transform, TransformResult,
    read_bronze, write_delta, silver_path, register,
)

logger = logging.getLogger(__name__)

# Loại chứng từ tính doanh thu (CHỈ PTT + CNT, PKK là thưởng)
DOANH_THU_MA_LOAI = ('PTT', 'CNT')


def _build_cns_doanhthu(df_cnsl):
    """
    Aggregate CongNoSoLuong → doanh thu theo ngày, schema PTHUBAOCO.

    Input:  df_cnsl (full CongNoSoLuong bronze, có nhiều MA_LOAI_CT, nhiều đối tượng)
    Output: DataFrame schema giống PTHUBAOCO_VIEW
    """
    if df_cnsl is None or df_cnsl.empty:
        return pd.DataFrame()

    # Filter loại chứng từ doanh thu
    mask = df_cnsl['MA_LOAI_CT'].isin(DOANH_THU_MA_LOAI)
    df = df_cnsl[mask].copy()
    if df.empty:
        return pd.DataFrame()

    # Parse ngày (API trả '2026-01-03T00:00:00' hoặc date)
    df['_ngay'] = pd.to_datetime(df['NGAY_CT']).dt.date

    # Group by ngày — gộp tất cả đối tượng, tất cả loại CT
    grp = df.groupby('_ngay', as_index=False).agg(
        ps_co=('PS_CO', 'sum'),
        ps_no=('PS_NO', 'sum'),
    )

    # Doanh thu = PS_CO - PS_NO
    grp['ps_co'] = grp['ps_co'] - grp['ps_no']

    # Build output theo schema PTHUBAOCO_VIEW
    out = pd.DataFrame({
        'ngay_ct': pd.to_datetime(grp['_ngay']),
        'ma_ct': 'CA1',
        'ma_kh_ct': 'TPBVSK',
        'ten_kh': 'TPBVSK',
        'dien_giai': 'Doanh thu Dược Sanfo',
        'ma_bp': 'TN',
        'ma_nvkd': 'TPBVSK',
        'tk_co': '131',
        'tk_no': '1111',
        'ps_co': grp['ps_co'].values,
    })

    return out


class PthuBaoCoTransform(Transform):
    name = 'PTHUBAOCO'

    def run(self) -> TransformResult:
        t0 = _time.time()
        try:
            # 1. Đọc Asia bronze
            df_asia = read_bronze('bronze.asia', 'fact', 'PTHUBAOCO')
            if df_asia is None:
                return TransformResult(
                    table=self.name, status='error',
                    seconds=round(_time.time() - t0, 2),
                    error='Asia PTHUBAOCO not found',
                )

            # 2. Đọc CNS bronze (có thể chưa có)
            df_cnsl = read_bronze('bronze.cns', 'fact', 'CongNoSoLuong')
            df_cns = _build_cns_doanhthu(df_cnsl)

            # 3. UNION
            if not df_cns.empty:
                # Đảm bảo cùng dtype ngay_ct
                if 'ngay_ct' in df_asia.columns:
                    df_asia['ngay_ct'] = pd.to_datetime(df_asia['ngay_ct'])
                df_merged = pd.concat([df_asia, df_cns], ignore_index=True)
                cns_rows = len(df_cns)
            else:
                df_merged = df_asia
                cns_rows = 0

            # 4. Ghi silver
            out = silver_path(self.name)
            version = write_delta(out, df_merged)
            elapsed = round(_time.time() - t0, 2)

            logger.info(f"[Transform] PTHUBAOCO: asia={len(df_asia)}, cns={cns_rows}, total={len(df_merged)}")

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


register(PthuBaoCoTransform())