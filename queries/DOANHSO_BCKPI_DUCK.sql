-- DOANHSO_BCKPI_DUCK.sql
-- $1=ngay_a, $2=ngay_b, $3=ma_bp
-- Trả về: ma_nvkd, ma_bp, doanhso (SUM)
SELECT
    CASE WHEN ma_nvkd = 'NVQ02' AND ma_bp = 'VB' THEN 'NVQ03' ELSE ma_nvkd END AS ma_nvkd,
    ma_bp,
    SUM(tien_nt2 - tien_ck_nt) AS doanhso
FROM BKHDBANHANG
WHERE ngay_ct >= CAST($1 AS DATE)
  AND ngay_ct <= CAST($2 AS DATE)
  AND ($3 = '' OR ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
GROUP BY CASE WHEN ma_nvkd = 'NVQ02' AND ma_bp = 'VB' THEN 'NVQ03' ELSE ma_nvkd END, ma_bp