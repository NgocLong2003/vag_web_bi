"""
elt/transform/thuong.py — Merge THUONG: Asia + CNS thưởng
============================================================
Asia:  bronze.asia/fact/THUONG.parquet
       Schema: ngay_ct, ma_kh_ct, ma_nvkd, dien_giai, thuong, ma_bp
CNS:   bronze.cns/fact/CongNoSoLuong.parquet
       → WHERE MA_LOAI_CT = 'PKK'
       → GROUP BY ngày → SUM(PS_CO - PS_NO) = thuong
       → gắn cố định ma_kh_ct='TPBVSK', ma_bp='TN', ...
Output: silver/THUONG (Delta Lake) = UNION(asia, cns_agg)
"""

import logging
import time as _time

import pandas as pd

from .base import (
    Transform, TransformResult,
    read_bronze, write_delta, silver_path, register,
)

logger = logging.getLogger(__name__)


def _build_cns_thuong(df_cnsl):
    """
    Aggregate CongNoSoLuong → thưởng theo ngày, schema THUONG_VIEW.
    """
    if df_cnsl is None or df_cnsl.empty:
        return pd.DataFrame()

    mask = df_cnsl['MA_LOAI_CT'] == 'PKK'
    df = df_cnsl[mask].copy()
    if df.empty:
        return pd.DataFrame()

    df['_ngay'] = pd.to_datetime(df['NGAY_CT']).dt.date

    grp = df.groupby('_ngay', as_index=False).agg(
        ps_co=('PS_CO', 'sum'),
        ps_no=('PS_NO', 'sum'),
    )

    # Thưởng = PS_CO - PS_NO
    grp['thuong'] = grp['ps_co'] - grp['ps_no']

    out = pd.DataFrame({
        'ngay_ct': pd.to_datetime(grp['_ngay']),
        'ma_kh_ct': 'TPBVSK',
        'ma_nvkd': 'TPBVSK',
        'dien_giai': 'Thưởng Dược Sanfo',
        'thuong': grp['thuong'].values,
        'ma_bp': 'TN',
    })

    return out


class ThuongTransform(Transform):
    name = 'THUONG'

    def run(self) -> TransformResult:
        t0 = _time.time()
        try:
            df_asia = read_bronze('bronze.asia', 'fact', 'THUONG')
            if df_asia is None:
                return TransformResult(
                    table=self.name, status='error',
                    seconds=round(_time.time() - t0, 2),
                    error='Asia THUONG not found',
                )

            df_cnsl = read_bronze('bronze.cns', 'fact', 'CongNoSoLuong')
            df_cns = _build_cns_thuong(df_cnsl)

            if not df_cns.empty:
                if 'ngay_ct' in df_asia.columns:
                    df_asia['ngay_ct'] = pd.to_datetime(df_asia['ngay_ct'])
                if 'thuong' in df_asia.columns:
                    df_asia['thuong'] = pd.to_numeric(df_asia['thuong'], errors='coerce').fillna(0)
                df_merged = pd.concat([df_asia, df_cns], ignore_index=True)
                cns_rows = len(df_cns)
            else:
                df_merged = df_asia
                cns_rows = 0

            out = silver_path(self.name)
            version = write_delta(out, df_merged)
            elapsed = round(_time.time() - t0, 2)

            logger.info(f"[Transform] THUONG: asia={len(df_asia)}, cns={cns_rows}, total={len(df_merged)}")

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


register(ThuongTransform())