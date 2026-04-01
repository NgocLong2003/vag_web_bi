WITH
    so_du_dau_nam AS (
        SELECT COALESCE(d.ma_kh, m.ma_kh) AS ma_kh,
            COALESCE(d.so_du, 0) + COALESCE(m.ps_mung1, 0) AS so_du_ban_dau
        FROM (
            SELECT ma_kh, SUM(du_no - du_co) AS so_du
            FROM CONGNOKHDK
            WHERE nam = $2 AND tk = '131'
            GROUP BY ma_kh
        ) d
        FULL OUTER JOIN (
            SELECT ma_kh, SUM(ps_no - ps_co) AS ps_mung1
            FROM BANGKECHUNGTU
            WHERE tk = '131' AND ngay_ct = make_date($2, 1, 1)
            GROUP BY ma_kh
        ) m ON d.ma_kh = m.ma_kh
    ),
    phatsinh AS (
        SELECT ma_kh, SUM(ps_no - ps_co) AS tong_phatsinh
        FROM BANGKECHUNGTU
        WHERE tk = '131'
          AND ngay_ct > make_date($2, 1, 1)
          AND ngay_ct <= CAST($1 AS DATE)
        GROUP BY ma_kh
    ),
    congno_fact AS (
        SELECT COALESCE(s.ma_kh, p.ma_kh) AS ma_kh,
            COALESCE(s.so_du_ban_dau, 0) AS so_du_ban_dau,
            COALESCE(p.tong_phatsinh, 0) AS tong_phatsinh,
            COALESCE(s.so_du_ban_dau, 0) + COALESCE(p.tong_phatsinh, 0) AS du_no_ck
        FROM so_du_dau_nam s
        FULL OUTER JOIN phatsinh p ON s.ma_kh = p.ma_kh
        WHERE COALESCE(s.so_du_ban_dau, 0) + COALESCE(p.tong_phatsinh, 0) != 0
    )
    SELECT cf.ma_kh, k.ten_kh, k.ma_bp, k.ma_nvkd,
           cf.so_du_ban_dau, cf.tong_phatsinh, cf.du_no_ck
    FROM congno_fact cf
    INNER JOIN DMKHACHHANG k ON cf.ma_kh = k.ma_kh
    WHERE 1=1
      AND ($3 = '' OR k.ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
      AND ($4 = '' OR k.ma_nvkd IN (SELECT TRIM(unnest(string_split($4, ',')))))
      AND ($5 = '' OR cf.ma_kh IN (SELECT TRIM(unnest(string_split($5, ',')))))
    ORDER BY cf.ma_kh