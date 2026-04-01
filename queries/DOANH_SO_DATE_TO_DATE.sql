DECLARE @NgayA DATE = '2025-01-01';
DECLARE @NgayB DATE = '2025-01-27';
DECLARE @MaBP NVARCHAR(50) = NULL;
DECLARE @DSMaNVKD NVARCHAR(MAX) = '';
DECLARE @DSMaKH NVARCHAR(MAX) = '';

SELECT 
    ma_kh,
    ma_bp,
    CASE 
        WHEN ma_nvkd = 'NVQ02' AND ma_bp = 'VB' THEN 'NVQ03'
        ELSE ma_nvkd 
    END AS ma_nvkd,
    SUM(so_luong) AS tong_so_luong,
    SUM(tien_nt2) AS tong_tien_nt2,
    SUM(tien_ck_nt) AS tong_tien_ck_nt,
    SUM(thue_gtgt_nt) AS tong_thue_gtgt_nt,
    SUM(tt_nt) AS tong_doanhso
FROM [dbo].[BKHDBANHANG_VIEW]
WHERE ngay_ct >= @NgayA
  AND ngay_ct <= @NgayB
  AND ma_bp != 'TN'
  AND (@MaBP IS NULL OR ma_bp = @MaBP)
  AND (@DSMaKH = '' OR ma_kh IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH, ',')))
  AND (@DSMaNVKD = '' OR 
       CASE WHEN ma_nvkd = 'NVQ02' AND ma_bp = 'VB' THEN 'NVQ03' ELSE ma_nvkd END 
       IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD, ',')))
GROUP BY 
    ma_kh, ma_bp,
    CASE WHEN ma_nvkd = 'NVQ02' AND ma_bp = 'VB' THEN 'NVQ03' ELSE ma_nvkd END
ORDER BY ma_kh, ma_nvkd;