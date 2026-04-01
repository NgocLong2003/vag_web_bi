-- $1=ngay_a, $2=ngay_b, $3=ngay_a2 (NULL=skip nhóm B), $4=ngay_b2, $5=ma_bp, $6=ds_nvkd, $7=ds_kh
WITH dt_raw AS (
    SELECT ngay_ct, ma_kh_ct, ma_bp, ps_co
    FROM PTHUBAOCO
    WHERE tk_co = '131' AND ma_bp != 'TN'
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
),
pairs AS (
    SELECT DISTINCT ma_kh_ct, ngay_ct FROM dt_raw
),
ds_hist AS (
    SELECT ds.ma_kh, ds.ma_nvkd, ds.ngay_ct
    FROM BKHDBANHANG ds
    WHERE ds.ma_kh IN (SELECT DISTINCT ma_kh_ct FROM pairs)
      AND ds.ngay_ct <= (SELECT MAX(ngay_ct) FROM pairs)
),
nvkd_map AS (
    SELECT p.ma_kh_ct, p.ngay_ct, ds.ma_nvkd,
        ROW_NUMBER() OVER (PARTITION BY p.ma_kh_ct, p.ngay_ct ORDER BY ds.ngay_ct DESC) AS rn
    FROM pairs p
    INNER JOIN ds_hist ds ON ds.ma_kh = p.ma_kh_ct AND ds.ngay_ct <= p.ngay_ct
),
nvkd_best AS (
    SELECT ma_kh_ct, ngay_ct, ma_nvkd FROM nvkd_map WHERE rn = 1
),
dmkh AS (
    SELECT DISTINCT ma_kh, ma_nvkd FROM DMKHACHHANG
    WHERE ma_kh IN (SELECT DISTINCT ma_kh_ct FROM pairs)
)
SELECT dt.ngay_ct,
    CASE WHEN dt.ngay_ct < '2026-02-01' THEN dt.ngay_ct - INTERVAL 1 DAY ELSE dt.ngay_ct END AS ngay_admin,
    dt.ma_kh_ct AS ma_kh,
    dt.ma_bp,
    COALESCE(m.ma_nvkd, dmkh.ma_nvkd) AS ma_nvkd,
    SUM(dt.ps_co) AS doanhthu
FROM dt_raw dt
LEFT JOIN nvkd_best m ON m.ma_kh_ct = dt.ma_kh_ct AND m.ngay_ct = dt.ngay_ct
LEFT JOIN dmkh ON dmkh.ma_kh = dt.ma_kh_ct
WHERE $6 = '' OR COALESCE(m.ma_nvkd, dmkh.ma_nvkd) IN (SELECT TRIM(unnest(string_split($6, ','))))
GROUP BY dt.ngay_ct, dt.ma_kh_ct, dt.ma_bp, COALESCE(m.ma_nvkd, dmkh.ma_nvkd),
    CASE WHEN dt.ngay_ct < '2026-02-01' THEN dt.ngay_ct - INTERVAL 1 DAY ELSE dt.ngay_ct END
ORDER BY ngay_admin, ma_kh, ma_nvkd