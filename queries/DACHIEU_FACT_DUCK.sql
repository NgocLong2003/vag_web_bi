-- DACHIEU_FACT_DUCK
-- Fact dòng-hàng cho Báo cáo Đa Chiều (chiều Sản phẩm / Khu vực)
-- Grain: NVKD × Khu vực × Khách hàng × Dòng SP × Sản phẩm — đo: số lượng, doanh số
-- Lọc theo ngay_ct + chuẩn hoá ma_nvkd y hệt DOANHSO_SQL_DUCK
--   → tổng doanh số/số lượng theo (NVKD,KH) KHỚP với chế độ NVKD×Kỳ.
-- $1=ngay_a, $2=ngay_b, $3=ma_bp, $4=ds_nvkd, $5=ds_kh
SELECT
    CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03' ELSE b.ma_nvkd END AS ma_nvkd,
    b.ma_kh,
    COALESCE(NULLIF(kh.ten_kh, ''), b.ma_kh) AS ten_kh,
    COALESCE(NULLIF(kh.ten_plkh1, ''), '(Không khu vực)') AS ten_plkh1,
    b.ma_vt,
    COALESCE(NULLIF(b.ten_vt, ''), b.ma_vt) AS ten_vt,
    COALESCE(NULLIF(d.ten_thuoc, ''), '(Không dòng SP)') AS ten_thuoc,
    SUM(b.so_luong) AS so_luong,
    SUM(b.tien_nt2 - b.tien_ck_nt) AS doanhso
FROM BKHDBANHANG b
LEFT JOIN DMKHACHHANG kh ON kh.ma_kh = b.ma_kh
LEFT JOIN DMSANPHAM d ON d.ma_vt = b.ma_vt
WHERE b.ngay_ct >= CAST($1 AS DATE)
  AND b.ngay_ct <= CAST($2 AS DATE)
  AND ($3 = '' OR b.ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
  AND ($4 = '' OR
       CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03' ELSE b.ma_nvkd END
       IN (SELECT TRIM(unnest(string_split($4, ',')))))
  AND ($5 = '' OR b.ma_kh IN (SELECT TRIM(unnest(string_split($5, ',')))))
GROUP BY
    CASE WHEN b.ma_nvkd = 'NVQ02' AND b.ma_bp = 'VB' THEN 'NVQ03' ELSE b.ma_nvkd END,
    b.ma_kh,
    COALESCE(NULLIF(kh.ten_kh, ''), b.ma_kh),
    COALESCE(NULLIF(kh.ten_plkh1, ''), '(Không khu vực)'),
    b.ma_vt,
    COALESCE(NULLIF(b.ten_vt, ''), b.ma_vt),
    COALESCE(NULLIF(d.ten_thuoc, ''), '(Không dòng SP)')
