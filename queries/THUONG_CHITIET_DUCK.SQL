-- $1=ngay_a, $2=ngay_b, $3=ma_kh
SELECT ngay_ct, ma_kh_ct AS ma_kh, ma_nvkd, dien_giai, thuong
FROM THUONG
WHERE ma_kh_ct = $3
  AND ngay_ct >= CAST($1 AS DATE) AND ngay_ct <= CAST($2 AS DATE)
ORDER BY ngay_ct