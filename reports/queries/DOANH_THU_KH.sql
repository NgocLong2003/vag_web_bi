DECLARE @NgayA DATE='2026-01-02';
DECLARE @NgayB DATE='2026-01-31';
DECLARE @MaBP NVARCHAR(MAX)='VB'; 
DECLARE @DSMaNVKD NVARCHAR(MAX)=''; 
DECLARE @DSMaKH NVARCHAR(MAX)='';

-- Lấy toàn bộ các dòng chi tiết từ PTHUBAOCO_VIEW (không GROUP BY, giữ đủ cột)
SELECT dt.ngay_ct, dt.ma_kh_ct, dt.ma_bp, dt.ps_co, dt.ten_kh, dt.dien_giai
INTO #TempDoanhThu_DT FROM PTHUBAOCO_VIEW dt
WHERE dt.tk_co='131' AND dt.ma_bp!='TN'
  AND ((dt.ngay_ct>='2026-01-01' AND dt.tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
    OR (dt.ngay_ct<'2026-01-01' AND dt.ma_ct='CA1'))
  AND (@MaBP IS NULL OR @MaBP='' OR dt.ma_bp IN (SELECT TRIM(value) FROM STRING_SPLIT(@MaBP,',')))
  AND dt.ngay_ct>=@NgayA AND dt.ngay_ct<=@NgayB
  AND (@DSMaKH='' OR dt.ma_kh_ct IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH,',')));

CREATE INDEX IX_Temp_DT_KH ON #TempDoanhThu_DT(ma_kh_ct, ngay_ct);

SELECT DISTINCT ma_kh_ct INTO #MaKH_CanTim_DT FROM #TempDoanhThu_DT;

SELECT ds.ma_kh, ds.ma_nvkd, ds.ngay_ct INTO #TempDoanhSo_DT
FROM BKHDBANHANG_VIEW ds INNER JOIN #MaKH_CanTim_DT mk ON ds.ma_kh=mk.ma_kh_ct;

CREATE INDEX IX_Temp_DS_DT ON #TempDoanhSo_DT(ma_kh, ngay_ct DESC);

SELECT dmkh.ma_kh, dmkh.ma_nvkd INTO #TempDMKH_DT
FROM DMKHACHHANG_VIEW dmkh INNER JOIN #MaKH_CanTim_DT mk ON dmkh.ma_kh=mk.ma_kh_ct;

CREATE INDEX IX_Temp_DMKH_DT ON #TempDMKH_DT(ma_kh);

-- Không GROUP BY, giữ nguyên từng dòng chi tiết, chỉ bổ sung ma_nvkd
SELECT
    dt.ngay_ct,
    CASE WHEN dt.ngay_ct<'2026-02-01' THEN DATEADD(DAY,-1,dt.ngay_ct) ELSE dt.ngay_ct END AS ngay_admin,
    dt.ma_kh_ct AS ma_kh,
    dt.ten_kh,
    dt.dien_giai,
    dt.ma_bp,
    COALESCE(ds.ma_nvkd, dmkh.ma_nvkd) AS ma_nvkd,
    dt.ps_co AS doanhthu
INTO #KetQua_DT
FROM #TempDoanhThu_DT dt
OUTER APPLY (
    SELECT TOP 1 ma_nvkd
    FROM #TempDoanhSo_DT tds
    WHERE tds.ma_kh=dt.ma_kh_ct AND tds.ngay_ct<=dt.ngay_ct
    ORDER BY tds.ngay_ct DESC
) ds
OUTER APPLY (
    SELECT TOP 1 ma_nvkd
    FROM #TempDMKH_DT tdmkh
    WHERE tdmkh.ma_kh=dt.ma_kh_ct
) dmkh
WHERE @DSMaNVKD='' OR COALESCE(ds.ma_nvkd, dmkh.ma_nvkd) IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD,','));

SELECT ngay_ct, ngay_admin, ma_kh, ten_kh, dien_giai, ma_bp, ma_nvkd, doanhthu
FROM #KetQua_DT
ORDER BY ngay_admin, ma_kh, ma_nvkd;

DROP TABLE IF EXISTS #TempDoanhThu_DT;
DROP TABLE IF EXISTS #MaKH_CanTim_DT;
DROP TABLE IF EXISTS #TempDoanhSo_DT;
DROP TABLE IF EXISTS #TempDMKH_DT;
DROP TABLE IF EXISTS #KetQua_DT;