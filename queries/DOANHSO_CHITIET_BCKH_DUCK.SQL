-- $1=ngay_a, $2=ngay_b, $3=ma_kh
SELECT ngay_ct,
    CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END AS ngay_admin,
    ma_kh, ma_vt, ten_vt, dvt, so_luong, gia_nt2, tien_nt2, tien_ck_nt, thue_gtgt_nt,
    tien_nt2 - tien_ck_nt AS doanhso
FROM BKHDBANHANG
WHERE ma_kh = $3
  AND CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END >= CAST($1 AS DATE)
  AND CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END <= CAST($2 AS DATE)
ORDER BY ngay_ct