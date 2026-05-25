"""
elt/transform/bangkechungtu.py — Merge BANGKECHUNGTU: Asia + CNS công nợ
==========================================================================
Asia:  bronze.asia/fact/BANGKECHUNGTU.parquet
       Schema: ma_kh, tk, ma_ct, ngay_ct, ps_no, ps_co
CNS:   bronze.cns/fact/CongNoSoLuong.parquet
       → Map MA_LOAI_CT → ma_ct, giữ nguyên PS_NO/PS_CO theo từng dòng
       → gắn ma_kh='TPBVSK', tk='131'

Mapping:
  HHA         → ma_ct='SO3'  (doanh số)
  HBTL        → ma_ct='SO4'  (trả lại)
  PTT, CNT    → ma_ct='CA1'  (doanh thu)
  PKK         → ma_ct='AR4'  (thưởng)

Output: silver/BANGKECHUNGTU (Delta Lake) = UNION(asia, cns_mapped)
"""

import logging
import time as _time

import pandas as pd

from .base import (
    Transform, TransformResult,
    read_bronze, write_delta, silver_path, register,
)

logger = logging.getLogger(__name__)

# Mapping MA_LOAI_CT (CNS) → ma_ct (AsiaSoft)
MA_LOAI_TO_MA_CT = {
    'HHA':  'SO3',   # doanh số
    'HBTL': 'SO4',   # trả lại
    'PTT':  'CA1',   # doanh thu
    'CNT':  'CA1',   # doanh thu
    'PKK':  'AR4',   # thưởng
}


def _build_cns_bangke(df_cnsl):
    """
    Map CongNoSoLuong → schema BANGKECHUNGTU_VIEW.
    Giữ nguyên PS_NO/PS_CO từng dòng, KHÔNG aggregate.
    Chỉ lấy các MA_LOAI_CT có trong mapping.
    """
    if df_cnsl is None or df_cnsl.empty:
        return pd.DataFrame()

    # Filter chỉ loại CT có mapping
    mask = df_cnsl['MA_LOAI_CT'].isin(MA_LOAI_TO_MA_CT.keys())
    df = df_cnsl[mask].copy()
    if df.empty:
        return pd.DataFrame()

    # Map ma_ct
    df['ma_ct'] = df['MA_LOAI_CT'].map(MA_LOAI_TO_MA_CT)

    # Parse ngày
    df['ngay_ct'] = pd.to_datetime(df['NGAY_CT'])

    # Ép numeric
    df['PS_NO'] = pd.to_numeric(df['PS_NO'], errors='coerce').fillna(0)
    df['PS_CO'] = pd.to_numeric(df['PS_CO'], errors='coerce').fillna(0)

    # Build output theo schema BANGKECHUNGTU
    out = pd.DataFrame({
        'ma_kh': 'TPBVSK',
        'tk': '131',
        'ma_ct': df['ma_ct'].values,
        'ngay_ct': df['ngay_ct'].values,
        'ps_no': df['PS_NO'].values,
        'ps_co': df['PS_CO'].values,
    })

    return out


class BangKeChungTuTransform(Transform):
    name = 'BANGKECHUNGTU'

    def run(self) -> TransformResult:
        t0 = _time.time()
        try:
            df_asia = read_bronze('bronze.asia', 'fact', 'BANGKECHUNGTU')
            if df_asia is None:
                return TransformResult(
                    table=self.name, status='error',
                    seconds=round(_time.time() - t0, 2),
                    error='Asia BANGKECHUNGTU not found',
                )

            df_cnsl = read_bronze('bronze.cns', 'fact', 'CongNoSoLuong')
            df_cns = _build_cns_bangke(df_cnsl)

            if not df_cns.empty:
                if 'ngay_ct' in df_asia.columns:
                    df_asia['ngay_ct'] = pd.to_datetime(df_asia['ngay_ct'])
                for col in ['ps_no', 'ps_co']:
                    if col in df_asia.columns:
                        df_asia[col] = pd.to_numeric(df_asia[col], errors='coerce').fillna(0)
                df_merged = pd.concat([df_asia, df_cns], ignore_index=True)
                cns_rows = len(df_cns)
            else:
                df_merged = df_asia
                cns_rows = 0

            out = silver_path(self.name)
            version = write_delta(out, df_merged)
            elapsed = round(_time.time() - t0, 2)

            logger.info(f"[Transform] BANGKECHUNGTU: asia={len(df_asia)}, cns={cns_rows}, total={len(df_merged)}")

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


register(BangKeChungTuTransform())