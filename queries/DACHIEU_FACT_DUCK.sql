-- DACHIEU_FACT_DUCK
-- Fact dòng-hàng cho Báo cáo Đa Chiều (chiều Sản phẩm / Khu vực)
-- Grain: NVKD × Khu vực × Khách hàng × Dòng SP × Sản phẩm
-- Đo (chỉ các chỉ số tách được theo sản phẩm): số lượng, doanh số, TRẢ LẠI
--   (doanh thu / thưởng / công nợ KHÔNG tách theo SP → tính ở nguồn aggregate NVKD×KH)
-- Lọc theo ngay_ct + chuẩn hoá ma_nvkd y hệt DOANHSO_SQL_DUCK / TRALAI_SQL_DUCK
-- $1=ngay_a, $2=ngay_b, $3=ma_bp, $4=ds_nvkd, $5=ds_kh
WITH combined AS (
    SELECT
        CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03' ELSE b.ma_nvkd END AS ma_nvkd,
        b.ma_kh, b.ma_vt, b.ten_vt, b.ma_bp,
        b.so_luong AS so_luong,
        b.tien_nt2 - b.tien_ck_nt AS doanhso,
        0 AS tralai
    FROM BKHDBANHANG b
    WHERE b.ngay_ct >= CAST($1 AS DATE) AND b.ngay_ct <= CAST($2 AS DATE)
    UNION ALL
    SELECT
        CASE WHEN t.ma_nvkd = 'NVQ02' AND t.ma_bp = 'VB' THEN 'NVQ03' ELSE t.ma_nvkd END AS ma_nvkd,
        t.ma_kh, t.ma_vt, t.ten_vt, t.ma_bp,
        0 AS so_luong,
        0 AS doanhso,
        t.tien_nt2 - t.tien_ck_nt AS tralai
    FROM TRALAI t
    WHERE t.ngay_ct >= CAST($1 AS DATE) AND t.ngay_ct <= CAST($2 AS DATE)
)
SELECT
    c.ma_nvkd,
    c.ma_kh,
    COALESCE(NULLIF(kh.ten_kh, ''), c.ma_kh) AS ten_kh,
    COALESCE(NULLIF(kh.ten_plkh1, ''), '(Không khu vực)') AS ten_plkh1,
    c.ma_vt,
    COALESCE(NULLIF(c.ten_vt, ''), c.ma_vt) AS ten_vt,
    COALESCE(NULLIF(d.ten_thuoc, ''), '(Không dòng SP)') AS ten_thuoc,
    SUM(c.so_luong) AS so_luong,
    SUM(c.doanhso) AS doanhso,
    SUM(c.tralai) AS tralai
FROM combined c
LEFT JOIN DMKHACHHANG kh ON kh.ma_kh = c.ma_kh
LEFT JOIN DMSANPHAM d ON d.ma_vt = c.ma_vt
WHERE ($3 = '' OR c.ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
  AND ($4 = '' OR c.ma_nvkd IN (SELECT TRIM(unnest(string_split($4, ',')))))
  AND ($5 = '' OR c.ma_kh IN (SELECT TRIM(unnest(string_split($5, ',')))))
GROUP BY
    c.ma_nvkd, c.ma_kh,
    COALESCE(NULLIF(kh.ten_kh, ''), c.ma_kh),
    COALESCE(NULLIF(kh.ten_plkh1, ''), '(Không khu vực)'),
    c.ma_vt,
    COALESCE(NULLIF(c.ten_vt, ''), c.ma_vt),
    COALESCE(NULLIF(d.ten_thuoc, ''), '(Không dòng SP)')
