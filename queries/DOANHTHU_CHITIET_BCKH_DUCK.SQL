-- $1=ngay_a, $2=ngay_b, $3=ma_kh
SELECT ngay_ct,
    CASE WHEN ngay_ct < '2026-02-01' THEN ngay_ct - INTERVAL 1 DAY ELSE ngay_ct END AS ngay_admin,
    ma_kh_ct AS ma_kh, ten_kh, dien_giai, ma_bp,
    ps_co AS doanhthu
FROM PTHUBAOCO
WHERE tk_co = '131' AND ma_bp != 'TN' AND ma_kh_ct = $3
  AND (
    (ngay_ct >= '2026-01-01' AND tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
    OR (ngay_ct < '2026-01-01' AND ma_ct = 'CA1')
  )
  AND ngay_ct >= CAST($1 AS DATE) AND ngay_ct <= CAST($2 AS DATE)
ORDER BY ngay_ct