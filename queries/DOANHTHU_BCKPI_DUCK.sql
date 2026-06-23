-- DOANHTHU_BCKPI_DUCK.sql
-- $1=ngay_bd_thu_tien, $2=ngay_kt_thu_tien (for VA/VB/SF)
-- $3=ngay_bd_xuat_ban (for others, NULL=skip), $4=ngay_kt_xuat_ban
-- $5=ma_bp filter (''=all)
-- Trả về: ma_nvkd, ma_bp, doanhthu (SUM)
--
-- ma_nvkd đã được điền đầy đủ ở extract (OUTER APPLY dim_khachhang_history)
--
SELECT
    ma_nvkd,
    ma_bp,
    SUM(ps_co) AS doanhthu
FROM PTHUBAOCO
WHERE tk_co = '131'
  AND (
    (ngay_ct >= '2026-01-01' AND tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
    OR (ngay_ct < '2026-01-01' AND ma_ct = 'CA1')
  )
  AND ($5 = '' OR ma_bp IN (SELECT TRIM(unnest(string_split($5, ',')))))
  AND (
    (ma_bp IN ('VA','VB','SF') AND ngay_ct >= CAST($1 AS DATE) AND ngay_ct <= CAST($2 AS DATE))
    OR
    (ma_bp NOT IN ('VA','VB','SF') AND $3 IS NOT NULL AND ngay_ct >= CAST($3 AS DATE) AND ngay_ct <= CAST($4 AS DATE))
  )
GROUP BY ma_nvkd, ma_bp