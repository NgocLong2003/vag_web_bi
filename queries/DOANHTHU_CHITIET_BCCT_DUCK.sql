-- $1=ngay_a, $2=ngay_b, $3=ma_bp, $4=ds_nvkd, $5=ds_kh
WITH dt_raw AS (
    SELECT ngay_ct, ma_kh_ct, ma_bp, ps_co, ten_kh, dien_giai, ma_nvkd AS ma_nvkd_pt
    FROM PTHUBAOCO
    WHERE tk_co = '131' AND ma_bp != 'TN'
      AND (
        (ngay_ct >= '2026-01-01' AND tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
        OR (ngay_ct < '2026-01-01' AND ma_ct = 'CA1')
      )
      AND ($3 = '' OR ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
      AND ngay_ct >= CAST($1 AS DATE) AND ngay_ct <= CAST($2 AS DATE)
      AND ($5 = '' OR ma_kh_ct IN (SELECT TRIM(unnest(string_split($5, ',')))))
),
all_kh AS (
    SELECT DISTINCT ma_kh_ct FROM dt_raw
    WHERE ma_nvkd_pt IS NULL OR ma_nvkd_pt = ''
),
ds_hist AS (
    SELECT ds.ma_kh, ds.ma_nvkd, ds.ngay_ct
    FROM BKHDBANHANG ds
    INNER JOIN all_kh ak ON ds.ma_kh = ak.ma_kh_ct
),
dmkh AS (
    SELECT DISTINCT ma_kh, ma_nvkd
    FROM DMKHACHHANG
    WHERE ma_kh IN (SELECT ma_kh_ct FROM all_kh)
),
dt_with_nvkd AS (
    SELECT dt.ngay_ct,
        CASE WHEN dt.ngay_ct < '2026-02-01' THEN dt.ngay_ct - INTERVAL 1 DAY ELSE dt.ngay_ct END AS ngay_admin,
        dt.ma_kh_ct AS ma_kh, dt.ten_kh, dt.dien_giai, dt.ma_bp,
        COALESCE(NULLIF(dt.ma_nvkd_pt, ''), ds.ma_nvkd, dmkh.ma_nvkd) AS ma_nvkd,
        dt.ps_co AS doanhthu
    FROM dt_raw dt
    LEFT JOIN LATERAL (
        SELECT ma_nvkd FROM ds_hist
        WHERE ma_kh = dt.ma_kh_ct AND ngay_ct <= dt.ngay_ct
        ORDER BY ngay_ct DESC LIMIT 1
    ) ds ON TRUE
    LEFT JOIN dmkh ON dmkh.ma_kh = dt.ma_kh_ct
)
SELECT ngay_ct, ngay_admin, ma_kh, ten_kh, dien_giai, ma_bp, ma_nvkd, doanhthu
FROM dt_with_nvkd
WHERE $4 = '' OR ma_nvkd IN (SELECT TRIM(unnest(string_split($4, ','))))
ORDER BY ngay_admin, ma_kh, ma_nvkd