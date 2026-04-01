-- $1=ngay_a_hang, $2=ngay_b_hang, $3=ngay_a_tien, $4=ngay_b_tien, $5=ma_bp, $6=ds_nvkd, $7=ds_kh
WITH ban_ra AS (
    SELECT ma_kh, SUM(ps_no - ps_co) AS ban_ra
    FROM BANGKECHUNGTU
    WHERE tk = '131' AND ma_ct = 'SO3'
      AND ngay_ct >= CAST($1 AS DATE) AND ngay_ct <= CAST($2 AS DATE)
    GROUP BY ma_kh
),
tra_ve AS (
    SELECT ma_kh, SUM(ps_co - ps_no) AS tra_ve
    FROM BANGKECHUNGTU
    WHERE tk = '131' AND ma_ct = 'SO4'
      AND ngay_ct >= CAST($1 AS DATE) AND ngay_ct <= CAST($2 AS DATE)
    GROUP BY ma_kh
),
thu_tien AS (
    SELECT ma_kh, SUM(ps_co - ps_no) AS dt_thuong
    FROM BANGKECHUNGTU
    WHERE tk = '131' AND ma_ct NOT IN ('SO3', 'SO4')
      AND ngay_ct >= CAST($3 AS DATE) AND ngay_ct <= CAST($4 AS DATE)
    GROUP BY ma_kh
),
tong_hop AS (
    SELECT
        COALESCE(b.ma_kh, t.ma_kh, tt.ma_kh) AS ma_kh,
        COALESCE(b.ban_ra, 0) AS ban_ra,
        COALESCE(t.tra_ve, 0) AS tra_ve,
        COALESCE(tt.dt_thuong, 0) AS dt_thuong,
        COALESCE(b.ban_ra, 0) - COALESCE(t.tra_ve, 0) - COALESCE(tt.dt_thuong, 0) AS du_no_trong_ky
    FROM ban_ra b
    FULL OUTER JOIN tra_ve t ON b.ma_kh = t.ma_kh
    FULL OUTER JOIN thu_tien tt ON COALESCE(b.ma_kh, t.ma_kh) = tt.ma_kh
    WHERE COALESCE(b.ban_ra, 0) - COALESCE(t.tra_ve, 0) - COALESCE(tt.dt_thuong, 0) != 0
)
SELECT th.ma_kh, k.ten_kh, k.ma_bp, k.ma_nvkd,
       th.ban_ra, th.tra_ve, th.dt_thuong, th.du_no_trong_ky
FROM tong_hop th
INNER JOIN DMKHACHHANG k ON th.ma_kh = k.ma_kh
WHERE ($5 = '' OR k.ma_bp IN (SELECT TRIM(unnest(string_split($5, ',')))))
  AND ($6 = '' OR k.ma_nvkd IN (SELECT TRIM(unnest(string_split($6, ',')))))
  AND ($7 = '' OR th.ma_kh IN (SELECT TRIM(unnest(string_split($7, ',')))))
ORDER BY th.ma_kh