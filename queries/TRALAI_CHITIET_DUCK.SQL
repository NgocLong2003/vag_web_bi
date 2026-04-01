-- $1=ngay_a, $2=ngay_b, $3=ma_kh
SELECT ngay_ct, ma_kh, ma_vt, ten_vt, dvt,
       so_luong, gia_nt2, tien_nt2, tien_ck_nt, thue_gtgt_nt,
       tien_nt2 - tien_ck_nt AS tralai
FROM TRALAI
WHERE ma_kh = $3
  AND ngay_ct >= CAST($1 AS DATE) AND ngay_ct <= CAST($2 AS DATE)
ORDER BY ngay_ct