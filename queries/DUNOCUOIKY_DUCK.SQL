-- $1=ngay_cut, $2=start_year, $3=ngay_a_lk, $4=ngay_b_lk, $5=has_lk, $6=ma_bp, $7=ds_nvkd, $8=ds_kh
--
-- Logic du_no_cuoi_ky:
-- ---------------------
-- Nếu YEAR(ngay_cut) < 2026:
--     du_no_cuoi_ky = du_no (công nợ tính đến ngay_cut, logic cũ)
--
-- Nếu YEAR(ngay_cut) >= 2026 (áp dụng KBC):
--     Xác định kỳ báo cáo (ky_year, ky_month) từ ngay_cut:
--         - DAY(ngay_cut) <= 15 → kỳ = tháng TRƯỚC (vì ngày 15 là cutoff của kỳ tháng trước)
--         - DAY(ngay_cut) >= 16 → kỳ = tháng HIỆN TẠI
--
--     du_no_cuoi_ky = so_du_dau_nam(2026)
--                   + SUM(SO3, SO4) trong [02/01/2026, cuối_tháng(ky_month)]  -- DS + TL theo tháng lịch
--                   + SUM(non-SO3/SO4) trong [02/01/2026, ngay_cut]            -- DT + Thưởng đến ngay_cut
--
--     Edge case tháng 1/2026: DS+TL chốt ở 31/01/2026
--
-- Các tham số ngay_a_lk, ngay_b_lk, has_lk được giữ lại trong signature nhưng KHÔNG được dùng
-- (logic mới tự derive kỳ KBC từ ngay_cut).
--
WITH 
-- Số dư đầu năm
so_du_dau_nam AS (
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

-- Công nợ (du_no) tính đến ngay_cut theo logic cũ — vẫn giữ để trả về như 1 cột riêng
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

-- Bán ra / Trả về trong kỳ lấn (theo tham số cũ, giữ lại để trả về cho UI nếu cần)
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

-- =========================================================
-- LOGIC MỚI: Tính phatsinh_kbc cho năm 2026+
-- =========================================================
-- Xác định kỳ báo cáo (ky_year, ky_month) từ ngay_cut
-- Và cutoff date của DS+TL (cuối tháng của kỳ báo cáo)
ky_bao_cao AS (
    SELECT
        CASE
            WHEN YEAR(CAST($1 AS DATE)) < 2026 THEN NULL
            WHEN DAY(CAST($1 AS DATE)) <= 15 AND MONTH(CAST($1 AS DATE)) = 1
                 THEN YEAR(CAST($1 AS DATE)) - 1
            WHEN DAY(CAST($1 AS DATE)) <= 15 THEN YEAR(CAST($1 AS DATE))
            ELSE YEAR(CAST($1 AS DATE))
        END AS ky_year,
        CASE
            WHEN YEAR(CAST($1 AS DATE)) < 2026 THEN NULL
            WHEN DAY(CAST($1 AS DATE)) <= 15 AND MONTH(CAST($1 AS DATE)) = 1 THEN 12
            WHEN DAY(CAST($1 AS DATE)) <= 15 THEN MONTH(CAST($1 AS DATE)) - 1
            ELSE MONTH(CAST($1 AS DATE))
        END AS ky_month
),

-- Phát sinh KBC (chỉ tính khi YEAR(ngay_cut) >= 2026)
-- SO3, SO4: từ đầu năm đến cuối tháng của kỳ báo cáo
-- Non-SO3/SO4: từ đầu năm đến ngay_cut
phatsinh_kbc AS (
    SELECT ma_kh, SUM(ps_no - ps_co) AS tong_phatsinh_kbc
    FROM BANGKECHUNGTU, ky_bao_cao
    WHERE tk = '131'
      AND ky_bao_cao.ky_year IS NOT NULL                      -- Chỉ áp dụng cho 2026+
      AND ngay_ct > make_date($2, 1, 1)                       -- Từ 02/01 năm $2 (giả định $2 = 2026 cho KBC)
      AND (
          -- SO3, SO4: đến cuối tháng của kỳ báo cáo
          (ma_ct IN ('SO3', 'SO4')
           AND ngay_ct <= (make_date(ky_bao_cao.ky_year, ky_bao_cao.ky_month, 1) + INTERVAL '1 month' - INTERVAL '1 day'))
          OR
          -- Non-SO3/SO4: đến ngay_cut
          (ma_ct NOT IN ('SO3', 'SO4')
           AND ngay_ct <= CAST($1 AS DATE))
      )
    GROUP BY ma_kh
),

-- Dư nợ cuối kỳ theo logic KBC mới (chỉ áp dụng cho 2026+)
du_no_ck_kbc AS (
    SELECT COALESCE(s.ma_kh, pk.ma_kh) AS ma_kh,
        COALESCE(s.so_du_ban_dau, 0) + COALESCE(pk.tong_phatsinh_kbc, 0) AS du_no_ck_kbc
    FROM so_du_dau_nam s
    FULL OUTER JOIN phatsinh_kbc pk ON s.ma_kh = pk.ma_kh
),

-- =========================================================
-- Gộp kết quả
-- =========================================================
ketqua AS (
    SELECT 
        COALESCE(c.ma_kh, d.ma_kh, k.ma_kh) AS ma_kh,
        COALESCE(c.du_no, 0) AS du_no,
        COALESCE(d.ban_ra_lk, 0) AS ban_ra_lk,
        COALESCE(d.tra_ve_lk, 0) AS tra_ve_lk,
        -- du_no_cuoi_ky:
        --   - Năm < 2026: = du_no (theo ngay_cut)
        --   - Năm >= 2026: = du_no_ck_kbc (theo logic KBC mới)
        CASE
            WHEN YEAR(CAST($1 AS DATE)) < 2026 THEN COALESCE(c.du_no, 0)
            ELSE COALESCE(k.du_no_ck_kbc, 0)
        END AS du_no_cuoi_ky
    FROM congno c
    FULL OUTER JOIN ds_lan_ki d ON c.ma_kh = d.ma_kh
    FULL OUTER JOIN du_no_ck_kbc k ON COALESCE(c.ma_kh, d.ma_kh) = k.ma_kh
    WHERE
        CASE
            WHEN YEAR(CAST($1 AS DATE)) < 2026 THEN COALESCE(c.du_no, 0)
            ELSE COALESCE(k.du_no_ck_kbc, 0)
        END != 0
)
SELECT kq.ma_kh, k.ten_kh, k.ma_bp, k.ma_nvkd,
       kq.du_no, kq.ban_ra_lk, kq.tra_ve_lk, kq.du_no_cuoi_ky
FROM ketqua kq
INNER JOIN DMKHACHHANG k ON kq.ma_kh = k.ma_kh
WHERE ($6 = '' OR k.ma_bp IN (SELECT TRIM(unnest(string_split($6, ',')))))
  AND ($7 = '' OR k.ma_nvkd IN (SELECT TRIM(unnest(string_split($7, ',')))))
  AND ($8 = '' OR kq.ma_kh IN (SELECT TRIM(unnest(string_split($8, ',')))))
ORDER BY kq.ma_kh