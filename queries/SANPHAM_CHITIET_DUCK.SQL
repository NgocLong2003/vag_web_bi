-- SANPHAM_CHITIET_DUCK
-- $1=ngay_a, $2=ngay_b, $3=ma_bp, $4=ds_nvkd, $5=ds_kh
SELECT
    b.ngay_ct,
    CASE WHEN b.ngay_ct < '2026-02-01' THEN b.ngay_ct - INTERVAL 1 DAY ELSE b.ngay_ct END AS ngay_admin,
    CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03' ELSE b.ma_nvkd END AS ma_nvkd,
    b.ma_kh, kh.ten_kh, b.ma_vt, b.ten_vt, b.dvt,
    b.so_luong, b.gia_nt2, b.tien_nt2, b.tien_ck_nt, b.ts_gtgt, b.thue_gtgt_nt,
    b.tien_nt2 - b.tien_ck_nt AS doanhso, b.ma_bp
FROM BKHDBANHANG b
LEFT JOIN DMKHACHHANG kh ON kh.ma_kh = b.ma_kh
WHERE CASE WHEN b.ngay_ct < '2026-02-01' THEN b.ngay_ct - INTERVAL 1 DAY ELSE b.ngay_ct END >= CAST($1 AS DATE)
  AND CASE WHEN b.ngay_ct < '2026-02-01' THEN b.ngay_ct - INTERVAL 1 DAY ELSE b.ngay_ct END <= CAST($2 AS DATE)
  AND ($3 = '' OR b.ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
  AND ($4 = '' OR
       CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03' ELSE b.ma_nvkd END
       IN (SELECT TRIM(unnest(string_split($4, ',')))))
  AND ($5 = '' OR b.ma_kh IN (SELECT TRIM(unnest(string_split($5, ',')))))
ORDER BY ngay_admin, b.ma_kh, ma_nvkd