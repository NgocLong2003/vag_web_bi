-- $1=ngay_a, $2=ngay_b, $3=ngay_a2 (NULL=skip nhóm B), $4=ngay_b2, $5=ma_bp, $6=ds_nvkd, $7=ds_kh
--
-- ma_nvkd đã được điền đầy đủ ở extract (OUTER APPLY dim_khachhang_history)
-- → không cần lookup ngược BKHDBANHANG/DMKHACHHANG nữa
--
SELECT ngay_ct,
    CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END AS ngay_admin,
    ma_kh_ct AS ma_kh,
    ma_bp,
    ma_nvkd,
    SUM(ps_co) AS doanhthu
FROM PTHUBAOCO
WHERE tk_co = '131'
  AND (
    (ngay_ct >= '2026-01-01' AND tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
    OR (ngay_ct < '2026-01-01' AND ma_ct = 'CA1')
  )
  AND ($5 = '' OR ma_bp IN (SELECT TRIM(unnest(string_split($5, ',')))))
  AND ($7 = '' OR ma_kh_ct IN (SELECT TRIM(unnest(string_split($7, ',')))))
  AND (
    (ma_bp IN ('VA','VB','SF') AND ngay_ct >= CAST($1 AS DATE) AND ngay_ct <= CAST($2 AS DATE))
    OR
    (ma_bp NOT IN ('VA','VB','SF') AND $3 IS NOT NULL AND ngay_ct >= CAST($3 AS DATE) AND ngay_ct <= CAST($4 AS DATE))
  )
  AND ($6 = '' OR ma_nvkd IN (SELECT TRIM(unnest(string_split($6, ',')))))
GROUP BY ngay_ct, ma_kh_ct, ma_bp, ma_nvkd,
    CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END
ORDER BY ngay_admin, ma_kh, ma_nvkd