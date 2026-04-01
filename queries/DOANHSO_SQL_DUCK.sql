SELECT ma_kh, ma_bp,
    CASE WHEN ma_nvkd = 'NVQ02' AND ma_bp = 'VB' THEN 'NVQ03'
            ELSE ma_nvkd END AS ma_nvkd,
    SUM(so_luong) AS tong_so_luong,
    SUM(tien_nt2) AS tong_tien_nt2,
    SUM(tien_ck_nt) AS tong_tien_ck_nt,
    SUM(thue_gtgt_nt) AS tong_thue_gtgt_nt,
    SUM(tien_nt2 - tien_ck_nt) AS tong_doanhso
FROM BKHDBANHANG
WHERE ngay_ct >= CAST($1 AS DATE)
    AND ngay_ct <= CAST($2 AS DATE)
    AND ($3 = '' OR ma_bp IN (SELECT TRIM(unnest(string_split($3, ',')))))
    AND ($5 = '' OR ma_kh IN (SELECT TRIM(unnest(string_split($5, ',')))))
    AND ($4 = '' OR
        CASE WHEN ma_nvkd = 'NVQ02' AND ma_bp = 'VB' THEN 'NVQ03'
            ELSE ma_nvkd END
        IN (SELECT TRIM(unnest(string_split($4, ',')))))
GROUP BY ma_kh, ma_bp,
    CASE WHEN ma_nvkd = 'NVQ02' AND ma_bp = 'VB' THEN 'NVQ03'
            ELSE ma_nvkd END
ORDER BY ma_kh, ma_nvkd
