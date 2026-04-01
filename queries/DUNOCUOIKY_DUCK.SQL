-- $1=ngay_cut, $2=start_year, $3=ngay_a_lk, $4=ngay_b_lk, $5=has_lk, $6=ma_bp, $7=ds_nvkd, $8=ds_kh
WITH so_du_dau_nam AS (
    SELECT COALESCE(d.ma_kh, m.ma_kh) AS ma_kh,
        COALESCE(d.so_du, 0) + COALESCE(m.ps_mung1, 0) AS so_du_ban_dau
    FROM (
        SELECT ma_kh, SUM(du_no - du_co) AS so_du
        FROM CONGNOKHDK WHERE nam = $2 AND tk = '131' GROUP BY ma_kh
    ) d
    FULL OUTER JOIN (
        SELECT ma_kh, SUM(ps_no - ps_co) AS ps_mung1
        FROM BANGKECHUNGTU WHERE tk = '131' AND ngay_ct = make_date($2, 1, 1) GROUP BY ma_kh
    ) m ON d.ma_kh = m.ma_kh
),
phatsinh AS (
    SELECT ma_kh, SUM(ps_no - ps_co) AS tong_phatsinh
    FROM BANGKECHUNGTU
    WHERE tk = '131' AND ngay_ct > make_date($2, 1, 1) AND ngay_ct <= CAST($1 AS DATE)
    GROUP BY ma_kh
),
congno AS (
    SELECT COALESCE(s.ma_kh, p.ma_kh) AS ma_kh,
        COALESCE(s.so_du_ban_dau, 0) + COALESCE(p.tong_phatsinh, 0) AS du_no
    FROM so_du_dau_nam s
    FULL OUTER JOIN phatsinh p ON s.ma_kh = p.ma_kh
),
ds_lan_ki AS (
    SELECT ma_kh,
        SUM(CASE WHEN ma_ct = 'SO3' THEN ps_no - ps_co ELSE 0 END) AS ban_ra_lk,
        SUM(CASE WHEN ma_ct = 'SO4' THEN ps_co - ps_no ELSE 0 END) AS tra_ve_lk
    FROM BANGKECHUNGTU
    WHERE tk = '131' AND ma_ct IN ('SO3', 'SO4')
      AND $5 = 1
      AND ngay_ct >= CAST($3 AS DATE) AND ngay_ct <= CAST($4 AS DATE)
    GROUP BY ma_kh
),
ketqua AS (
    SELECT COALESCE(c.ma_kh, d.ma_kh) AS ma_kh,
        COALESCE(c.du_no, 0) AS du_no,
        COALESCE(d.ban_ra_lk, 0) AS ban_ra_lk,
        COALESCE(d.tra_ve_lk, 0) AS tra_ve_lk,
        COALESCE(c.du_no, 0) - (COALESCE(d.ban_ra_lk, 0) - COALESCE(d.tra_ve_lk, 0)) AS du_no_cuoi_ky
    FROM congno c
    FULL OUTER JOIN ds_lan_ki d ON c.ma_kh = d.ma_kh
    WHERE COALESCE(c.du_no, 0) - (COALESCE(d.ban_ra_lk, 0) - COALESCE(d.tra_ve_lk, 0)) != 0
)
SELECT kq.ma_kh, k.ten_kh, k.ma_bp, k.ma_nvkd,
       kq.du_no, kq.ban_ra_lk, kq.tra_ve_lk, kq.du_no_cuoi_ky
FROM ketqua kq
INNER JOIN DMKHACHHANG k ON kq.ma_kh = k.ma_kh
WHERE ($6 = '' OR k.ma_bp IN (SELECT TRIM(unnest(string_split($6, ',')))))
  AND ($7 = '' OR k.ma_nvkd IN (SELECT TRIM(unnest(string_split($7, ',')))))
  AND ($8 = '' OR kq.ma_kh IN (SELECT TRIM(unnest(string_split($8, ',')))))
ORDER BY kq.ma_kh