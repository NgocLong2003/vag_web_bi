"""
elt/transform/tralai.py — Merge TRALAI: Asia + CNS hàng trả lại
=================================================================
Asia:  bronze.asia/fact/TRALAI.parquet
       Schema: ngay_ct, ma_kh, ma_vt, ten_vt, dvt, so_luong, gia_nt2,
               tien_nt2, tien_ck_nt, thue_gtgt_nt, ma_bp, ma_nvkd
CNS:   bronze.cns/fact/CongNoSoLuong.parquet
       → WHERE MA_LOAI_CT = 'HBTL'
       → GROUP BY ngày → SUM(PS_CO - PS_NO) = tien_nt2
       → gắn cố định ma_kh='TPBVSK', ma_bp='TN', ...
Output: silver/TRALAI (Delta Lake) = UNION(asia, cns_agg)
"""

import logging
import time as _time

import pandas as pd

from .base import (
    Transform, TransformResult,
    read_bronze, write_delta, silver_path, register,
)

logger = logging.getLogger(__name__)


def _build_cns_tralai(df_cnsl):
    """
    Aggregate CongNoSoLuong → trả lại theo ngày, schema TRALAI_VIEW.
    """
    if df_cnsl is None or df_cnsl.empty:
        return pd.DataFrame()

    mask = df_cnsl['MA_LOAI_CT'] == 'HBTL'
    df = df_cnsl[mask].copy()
    if df.empty:
        return pd.DataFrame()

    df['_ngay'] = pd.to_datetime(df['NGAY_CT']).dt.date

    grp = df.groupby('_ngay', as_index=False).agg(
        ps_co=('PS_CO', 'sum'),
        ps_no=('PS_NO', 'sum'),
    )

    # Trả lại = PS_CO - PS_NO
    grp['tien_nt2'] = grp['ps_co'] - grp['ps_no']

    out = pd.DataFrame({
        'ngay_ct': pd.to_datetime(grp['_ngay']),
        'ma_kh': 'TPBVSK',
        'ma_vt': 'TPBVSK',
        'ten_vt': 'TPBVSK',
        'dvt': '',
        'so_luong': 0.0,
        'gia_nt2': 0.0,
        'tien_nt2': grp['tien_nt2'].values,
        'tien_ck_nt': 0.0,
        'thue_gtgt_nt': 0.0,
        'ma_bp': 'TN',
        'ma_nvkd': 'TPBVSK',
    })

    return out


class TraLaiTransform(Transform):
    name = 'TRALAI'

    def run(self) -> TransformResult:
        t0 = _time.time()
        try:
            df_asia = read_bronze('bronze.asia', 'fact', 'TRALAI')
            if df_asia is None:
                return TransformResult(
                    table=self.name, status='error',
                    seconds=round(_time.time() - t0, 2),
                    error='Asia TRALAI not found',
                )

            df_cnsl = read_bronze('bronze.cns', 'fact', 'CongNoSoLuong')
            df_cns = _build_cns_tralai(df_cnsl)

            if not df_cns.empty:
                if 'ngay_ct' in df_asia.columns:
                    df_asia['ngay_ct'] = pd.to_datetime(df_asia['ngay_ct'])
                # Ép dtype số cho asia (tránh object mixed)
                num_cols = ['so_luong', 'gia_nt2', 'tien_nt2', 'tien_ck_nt', 'thue_gtgt_nt']
                for col in num_cols:
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

            logger.info(f"[Transform] TRALAI: asia={len(df_asia)}, cns={cns_rows}, total={len(df_merged)}")

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


register(TraLaiTransform())