DECLARE @NgayCut DATE = '2025-01-27';
DECLARE @StartYear INT = YEAR(@NgayCut);
DECLARE @MaBP NVARCHAR(50) = NULL;
DECLARE @DSMaNVKD NVARCHAR(MAX) = '';   -- VD: 'NV01,NV02,NV03' hoặc '' = tất cả
DECLARE @DSMaKH NVARCHAR(MAX) = '';     -- VD: 'KH01,KH02' hoặc '' = tất cả

;WITH 
so_du_dau_nam AS (
    SELECT 
        COALESCE(d.ma_kh, m.ma_kh) AS ma_kh,
        ISNULL(d.so_du, 0) + ISNULL(m.ps_mung1, 0) AS so_du_ban_dau
    FROM (
        SELECT ma_kh, SUM(du_no - du_co) AS so_du
        FROM [dbo].[CONGNOKHDK_VIEW]
        WHERE nam = @StartYear AND tk = '131'
        GROUP BY ma_kh
    ) d
    FULL OUTER JOIN (
        SELECT ma_kh, SUM(ps_no - ps_co) AS ps_mung1
        FROM [dbo].[BANGKECHUNGTU_VIEW]
        WHERE tk = '131' AND ngay_ct = DATEFROMPARTS(@StartYear, 1, 1)
        GROUP BY ma_kh
    ) m ON d.ma_kh = m.ma_kh
),
phatsinh AS (
    SELECT 
        ma_kh,
        SUM(ps_no - ps_co) AS tong_phatsinh
    FROM [dbo].[BANGKECHUNGTU_VIEW]
    WHERE tk = '131'
      AND ngay_ct > DATEFROMPARTS(@StartYear, 1, 1)
      AND ngay_ct <= @NgayCut
    GROUP BY ma_kh
)

SELECT 
    k.ma_kh, k.ten_kh, k.ma_bp, k.ma_nvkd,
    ISNULL(s.so_du_ban_dau, 0) AS so_du_ban_dau,
    ISNULL(p.tong_phatsinh, 0) AS tong_phatsinh,
    ISNULL(s.so_du_ban_dau, 0) + ISNULL(p.tong_phatsinh, 0) AS du_no_ck
FROM (
    SELECT DISTINCT ma_kh, ten_kh, ma_bp, ma_nvkd
    FROM [dbo].[DMKHACHHANG_VIEW]
    WHERE ma_bp IS NOT NULL AND ma_bp != 'TN' AND ma_kh != 'TTT'
      AND (@MaBP IS NULL OR ma_bp = @MaBP)
      AND (@DSMaNVKD = '' OR ma_nvkd IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaNVKD, ',')))
      AND (@DSMaKH = '' OR ma_kh IN (SELECT TRIM(value) FROM STRING_SPLIT(@DSMaKH, ',')))
) k
LEFT JOIN so_du_dau_nam s ON k.ma_kh = s.ma_kh
LEFT JOIN phatsinh p ON k.ma_kh = p.ma_kh
WHERE ISNULL(s.so_du_ban_dau, 0) + ISNULL(p.tong_phatsinh, 0) != 0
ORDER BY k.ma_kh;