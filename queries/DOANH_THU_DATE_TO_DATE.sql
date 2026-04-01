DECLARE @NgayA DATE = '2025-01-01';
DECLARE @NgayB DATE = '2025-01-27';
DECLARE @MaBP NVARCHAR(50) = NULL;
DECLARE @DSMaNVKD NVARCHAR(MAX) = 'CVT01,NHS01';
DECLARE @DSMaKH NVARCHAR(MAX) = '';

-- === PHẦN 1: DOANH SỐ DF ===
SELECT dt.ngay_ct, dt.ma_kh, dt.ma_bp, dt.ps_co
INTO #TempDoanhThu_DF
FROM [dbo].[BANGKECHUNGTU_VIEW] dt
WHERE ((dt.tk = '131' 
    AND (
        (dt.ngay_ct >= '2026-01-01' AND dt.tk_du IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
        OR (dt.ngay_ct < '2026-01-01' AND dt.ma_ct = 'CA1')
    )) OR dt.tk_du = '6351')
    AND dt.ma_bp = 'DF'
    AND (@MaBP IS NULL OR dt.ma_bp = @MaBP)
    AND dt.ngay_ct >= @NgayA AND dt.ngay_ct <= @NgayB
    AND (@DSMaKH = '' OR dt.ma_kh IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH, ',')))

CREATE INDEX IX_DF ON #TempDoanhThu_DF(ma_kh, ngay_ct)

SELECT DISTINCT ma_kh INTO #MaKH_DF FROM #TempDoanhThu_DF

SELECT ds.ma_kh, ds.ma_nvkd, ds.ngay_ct
INTO #TempDoanhSo_DF
FROM [dbo].[BKHDBANHANG_VIEW] ds
INNER JOIN #MaKH_DF mk ON ds.ma_kh = mk.ma_kh
CREATE INDEX IX_DS_DF ON #TempDoanhSo_DF(ma_kh, ngay_ct DESC)

SELECT dmkh.ma_kh, dmkh.ma_nvkd
INTO #TempDMKH_DF
FROM [dbo].[DMKHACHHANG_VIEW] dmkh
INNER JOIN #MaKH_DF mk ON dmkh.ma_kh = mk.ma_kh
CREATE INDEX IX_DMKH_DF ON #TempDMKH_DF(ma_kh)

SELECT
    dt.ma_kh, dt.ma_bp,
    COALESCE(ds.ma_nvkd, dmkh.ma_nvkd) AS ma_nvkd,
    SUM(dt.ps_co) AS doanhso_df
INTO #KetQua_DF
FROM #TempDoanhThu_DF dt
OUTER APPLY (
    SELECT TOP 1 ma_nvkd FROM #TempDoanhSo_DF tds
    WHERE tds.ma_kh = dt.ma_kh AND tds.ngay_ct <= dt.ngay_ct
    ORDER BY tds.ngay_ct DESC
) ds
OUTER APPLY (
    SELECT TOP 1 ma_nvkd FROM #TempDMKH_DF tdmkh
    WHERE tdmkh.ma_kh = dt.ma_kh
) dmkh
WHERE @DSMaNVKD = '' 
   OR COALESCE(ds.ma_nvkd, dmkh.ma_nvkd) IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD, ','))
GROUP BY dt.ma_kh, dt.ma_bp, COALESCE(ds.ma_nvkd, dmkh.ma_nvkd)

-- === PHẦN 2: DOANH THU ===
SELECT dt.ngay_ct, dt.ma_kh, dt.ma_kh_ct, dt.ma_bp, dt.ps_co
INTO #TempDoanhThu_DT
FROM [dbo].[PTHUBAOCO_VIEW] dt
WHERE dt.tk_co = '131' AND dt.ma_bp != 'TN' 
    AND (
        (dt.ngay_ct >= '2026-01-01' AND dt.tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
        OR (dt.ngay_ct < '2026-01-01' AND dt.ma_ct = 'CA1')
    )
    AND (@MaBP IS NULL OR dt.ma_bp = @MaBP)
    AND dt.ngay_ct >= @NgayA AND dt.ngay_ct <= @NgayB
    AND (@DSMaKH = '' OR dt.ma_kh_ct IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH, ',')))

CREATE INDEX IX_DT ON #TempDoanhThu_DT(ma_kh_ct, ngay_ct)

SELECT DISTINCT ma_kh_ct INTO #MaKH_DT FROM #TempDoanhThu_DT

SELECT ds.ma_kh, ds.ma_nvkd, ds.ngay_ct
INTO #TempDoanhSo_DT
FROM [dbo].[BKHDBANHANG_VIEW] ds
INNER JOIN #MaKH_DT mk ON ds.ma_kh = mk.ma_kh_ct
CREATE INDEX IX_DS_DT ON #TempDoanhSo_DT(ma_kh, ngay_ct DESC)

SELECT dmkh.ma_kh, dmkh.ma_nvkd
INTO #TempDMKH_DT
FROM [dbo].[DMKHACHHANG_VIEW] dmkh
INNER JOIN #MaKH_DT mk ON dmkh.ma_kh = mk.ma_kh_ct
CREATE INDEX IX_DMKH_DT ON #TempDMKH_DT(ma_kh)

SELECT
    dt.ma_kh, dt.ma_bp,
    COALESCE(ds.ma_nvkd, dmkh.ma_nvkd) AS ma_nvkd,
    SUM(dt.ps_co) AS doanhthu
INTO #KetQua_DT
FROM #TempDoanhThu_DT dt
OUTER APPLY (
    SELECT TOP 1 ma_nvkd FROM #TempDoanhSo_DT tds
    WHERE tds.ma_kh = dt.ma_kh_ct AND tds.ngay_ct <= dt.ngay_ct
    ORDER BY tds.ngay_ct DESC
) ds
OUTER APPLY (
    SELECT TOP 1 ma_nvkd FROM #TempDMKH_DT tdmkh
    WHERE tdmkh.ma_kh = dt.ma_kh_ct
) dmkh
WHERE @DSMaNVKD = '' 
   OR COALESCE(ds.ma_nvkd, dmkh.ma_nvkd) IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD, ','))
GROUP BY dt.ma_kh, dt.ma_bp, COALESCE(ds.ma_nvkd, dmkh.ma_nvkd)

-- === PHẦN 3: KẾT HỢP ===
SELECT
    COALESCE(df.ma_kh, dt.ma_kh) AS ma_kh,
    COALESCE(df.ma_bp, dt.ma_bp) AS ma_bp,
    COALESCE(df.ma_nvkd, dt.ma_nvkd) AS ma_nvkd,
    ISNULL(df.doanhso_df, 0) AS doanhso_df,
    ISNULL(dt.doanhthu, 0) AS doanhthu
FROM #KetQua_DF df
FULL OUTER JOIN #KetQua_DT dt 
    ON df.ma_kh = dt.ma_kh AND df.ma_nvkd = dt.ma_nvkd AND df.ma_bp = dt.ma_bp
ORDER BY ma_kh, ma_nvkd

-- CLEANUP
DROP TABLE #TempDoanhThu_DF, #MaKH_DF, #TempDoanhSo_DF, #TempDMKH_DF, #KetQua_DF
DROP TABLE #TempDoanhThu_DT, #MaKH_DT, #TempDoanhSo_DT, #TempDMKH_DT, #KetQua_DT