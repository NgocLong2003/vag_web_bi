-- $1=ngay_a, $2=ngay_b, $3=ma_bp, $4=ds_nvkd, $5=ds_kh
WITH dt_filtered AS (
    SELECT
        ngay_ct,
        CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END AS ngay_admin,
        YEAR(CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END) AS year_admin,
        MONTH(CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END) AS month_admin,
        ma_kh_ct AS ma_kh,
        ma_bp,
        ma_nvkd,
        ps_co AS doanhthu
    FROM PTHUBAOCO
    WHERE tk_co = '131' AND ma_bp != 'TN'
      AND (
        (ngay_ct >= '2026-01-01' AND tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
        OR (ngay_ct < '2026-01-01' AND ma_ct = 'CA1')
      )
      AND ngay_ct >= CAST($1 AS DATE)
      AND ngay_ct <= CAST($2 AS DATE)
      AND ($3 = '' OR ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
      AND ($5 = '' OR ma_kh_ct IN (SELECT TRIM(unnest(string_split($5, ',')))))
      AND ($4 = '' OR ma_nvkd IN (SELECT TRIM(unnest(string_split($4, ',')))))
)
SELECT ngay_ct, ngay_admin, year_admin, month_admin,
       ma_kh, ma_bp, ma_nvkd,
       SUM(doanhthu) AS doanhthu
FROM dt_filtered
GROUP BY ngay_ct, ngay_admin, year_admin, month_admin, ma_kh, ma_bp, ma_nvkd
ORDER BY ngay_admin, ma_kh, ma_nvkd