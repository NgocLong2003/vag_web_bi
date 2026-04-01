-- $1=ngay_a, $2=ngay_b, $3=ma_bp, $4=ds_nvkd, $5=ds_kh
SELECT
    ngay_ct,
    CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END AS ngay_admin,
    CASE WHEN ma_nvkd = 'NVQ02' AND ma_bp = 'VB' THEN 'NVQ03' ELSE ma_nvkd END AS ma_nvkd,
    ma_kh, ma_vt, ten_vt, dvt,
    so_luong, gia_nt2, tien_nt2, tien_ck_nt, ts_gtgt, thue_gtgt_nt,
    tien_nt2 - tien_ck_nt AS doanhso, ma_bp
FROM BKHDBANHANG
WHERE CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END >= CAST($1 AS DATE)
  AND CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END <= CAST($2 AS DATE)
  AND ($3 = '' OR ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
  AND ($4 = '' OR
       CASE WHEN ma_nvkd = 'NVQ02' AND ma_bp = 'VB' THEN 'NVQ03' ELSE ma_nvkd END
       IN (SELECT TRIM(unnest(string_split($4, ',')))))
  AND ($5 = '' OR ma_kh IN (SELECT TRIM(unnest(string_split($5, ',')))))
ORDER BY CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END, ma_kh, ma_nvkd