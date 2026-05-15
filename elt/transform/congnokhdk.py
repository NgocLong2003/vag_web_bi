"""
elt/transform/congnokhdk.py — Merge CONGNOKHDK: Asia + CNS số dư đầu năm
===========================================================================
Asia:  bronze.asia/fact/CONGNOKHDK.parquet
       Schema: ma_kh, nam, tk, du_no, du_co
CNS:   Thêm dòng TPBVSK cho mỗi năm có data trong CongNoSoLuong.
       du_no=0, du_co=0 (Sanfo không có số dư tồn trước khi bắt đầu giao dịch,
       toàn bộ công nợ tính từ phát sinh trong BANGKECHUNGTU).

Output: silver/CONGNOKHDK (Delta Lake) = UNION(asia, cns_rows)
"""

import logging
import time as _time

import pandas as pd

from .base import (
    Transform, TransformResult,
    read_bronze, write_delta, silver_path, register,
)

logger = logging.getLogger(__name__)


def _build_cns_congnokhdk(df_cnsl):
    """
    Tạo dòng CONGNOKHDK cho TPBVSK — 1 dòng mỗi năm có giao dịch.
    du_no=0, du_co=0 vì số dư ban đầu = 0.
    """
    if df_cnsl is None or df_cnsl.empty:
        return pd.DataFrame()

    # Lấy danh sách năm có giao dịch
    years = pd.to_datetime(df_cnsl['NGAY_CT']).dt.year.unique()
    if len(years) == 0:
        return pd.DataFrame()

    rows = []
    for y in sorted(years):
        rows.append({
            'ma_kh': 'TPBVSK',
            'nam': int(y),
            'tk': '131',
            'du_no': 0.0,
            'du_co': 0.0,
        })

    return pd.DataFrame(rows)


class CongNoKhDkTransform(Transform):
    name = 'CONGNOKHDK'

    def run(self) -> TransformResult:
        t0 = _time.time()
        try:
            df_asia = read_bronze('bronze.asia', 'fact', 'CONGNOKHDK')
            if df_asia is None:
                return TransformResult(
                    table=self.name, status='error',
                    seconds=round(_time.time() - t0, 2),
                    error='Asia CONGNOKHDK not found',
                )

            df_cnsl = read_bronze('bronze.cns', 'fact', 'CongNoSoLuong')
            df_cns = _build_cns_congnokhdk(df_cnsl)

            if not df_cns.empty:
                for col in ['du_no', 'du_co']:
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

            logger.info(f"[Transform] CONGNOKHDK: asia={len(df_asia)}, cns={cns_rows}, total={len(df_merged)}")

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


register(CongNoKhDkTransform())