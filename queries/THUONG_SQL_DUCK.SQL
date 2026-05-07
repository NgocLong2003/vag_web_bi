-- THUONG_SQL_DUCK
-- $1=ngay_a, $2=ngay_b, $3=ma_bp, $4=ds_nvkd, $5=ds_kh
SELECT ma_kh_ct AS ma_kh, ma_bp,
    ma_nvkd,
    SUM(thuong) AS tong_thuong
FROM THUONG
WHERE ngay_ct >= CAST($1 AS DATE)
  AND ngay_ct <= CAST($2 AS DATE)
  AND ($3 = '' OR ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
  AND ($5 = '' OR ma_kh_ct IN (SELECT TRIM(unnest(string_split($5, ',')))))
  AND ($4 = '' OR ma_nvkd IN (SELECT TRIM(unnest(string_split($4, ',')))))
GROUP BY ma_kh_ct, ma_bp, ma_nvkd
ORDER BY ma_kh_ct, ma_nvkd