-- THONGKE_LAYHANG_DUCK
-- $1=ngay_a, $2=ngay_b, $3=ma_bp, $4=ds_nvkd, $5=ds_kh
SELECT
    COALESCE(d.ten_thuoc, '') AS ten_thuoc,
    b.ma_vt, b.ten_vt,
    COALESCE(kh.ten_plkh1, '') AS ten_plkh3,
    b.ma_kh, kh.ten_kh,
    SUM(b.so_luong) AS so_luong,
    SUM(b.tien_nt2 - b.tien_ck_nt) AS doanhso
FROM BKHDBANHANG b
LEFT JOIN DMKHACHHANG kh ON kh.ma_kh = b.ma_kh
LEFT JOIN DMSANPHAM d ON d.ma_vt = b.ma_vt
WHERE CASE WHEN b.ngay_ct < '2026-02-01' THEN b.ngay_ct - INTERVAL 1 DAY ELSE b.ngay_ct END >= CAST($1 AS DATE)
  AND CASE WHEN b.ngay_ct < '2026-02-01' THEN b.ngay_ct - INTERVAL 1 DAY ELSE b.ngay_ct END <= CAST($2 AS DATE)
  AND ($3 = '' OR b.ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
  AND ($4 = '' OR
       CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03' ELSE b.ma_nvkd END
       IN (SELECT TRIM(unnest(string_split($4, ',')))))
  AND ($5 = '' OR b.ma_kh IN (SELECT TRIM(unnest(string_split($5, ',')))))
GROUP BY COALESCE(d.ten_thuoc, ''), b.ma_vt, b.ten_vt,
    COALESCE(kh.ten_plkh1, ''), b.ma_kh, kh.ten_kh
ORDER BY COALESCE(d.ten_thuoc, ''), b.ten_vt, COALESCE(kh.ten_plkh1, ''), kh.ten_kh