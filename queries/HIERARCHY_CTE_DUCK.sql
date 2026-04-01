WITH RECURSIVE NV_BASE AS (
        SELECT ma_nvkd,
               CASE
                 WHEN ma_nvkd = 'DTD01' THEN 'TVV01'
                 WHEN ma_nvkd = 'PQT01' THEN 'TVV01'
                 WHEN ma_nvkd = 'BCT02' THEN 'TVV01'
                 WHEN ma_nvkd = 'NTT02' THEN 'TVV01'
                 ELSE ma_ql
               END AS ma_ql,
               ten_nvkd
        FROM DMNHANVIENKD
        UNION ALL SELECT 'VB99','VB00','Khác'
        UNION ALL SELECT 'VA99','TVV01','Khác'
        UNION ALL SELECT 'SF99','PVT04','Khác'
        UNION ALL SELECT 'DF99','NVD01','Khác'
        UNION ALL SELECT 'XK99','XK00','Khác'
        UNION ALL SELECT 'DA99','DA00','Khác'
    ),
    RecursiveHierarchy AS (
        SELECT v.ma_nvkd, v.ma_ql, v.ten_nvkd,
            CAST(v.ma_nvkd AS VARCHAR) AS stt_nhom, 0 AS level
        FROM NV_BASE v
        LEFT JOIN NV_BASE parent ON v.ma_ql = parent.ma_nvkd
        WHERE v.ma_ql IS NULL OR v.ma_ql = '' OR parent.ma_nvkd IS NULL
        UNION ALL
        SELECT e.ma_nvkd, e.ma_ql, e.ten_nvkd,
            CAST(rh.stt_nhom || '.' || e.ma_nvkd AS VARCHAR), rh.level + 1
        FROM NV_BASE e
        INNER JOIN RecursiveHierarchy rh ON e.ma_ql = rh.ma_nvkd
    )
    SELECT ma_nvkd, ten_nvkd, ma_ql, stt_nhom, level
    FROM RecursiveHierarchy ORDER BY stt_nhom
