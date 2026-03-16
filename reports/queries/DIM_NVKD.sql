WITH RecursiveHierarchy AS (
    -- Anchor: Lấy tất cả nhân viên là root (không có quản lý HOẶC quản lý không tồn tại)
    SELECT 
        v.ma_nvkd,
        v.ma_ql,
        v.ten_nvkd,
        CAST(v.ma_nvkd AS NVARCHAR(MAX)) AS stt_nhom,
        0 AS level
    FROM (
        -- Dữ liệu từ VIEW gốc
        SELECT ma_nvkd, ma_ql, ten_nvkd
        FROM DMNHANVIENKD_VIEW
        
        UNION ALL
        
        -- Thêm các dòng "Khác" mới
        SELECT 'VB99' AS ma_nvkd, 'VB00' AS ma_ql, N'Khác' AS ten_nvkd
        UNION ALL
        SELECT 'VA99', 'TVV01', N'Khác'
        UNION ALL
        SELECT 'SF99', 'PVT04', N'Khác'
        UNION ALL
        SELECT 'DF99', 'NVD01', N'Khác'
        UNION ALL
        SELECT 'XK99', 'XK00', N'Khác'
        UNION ALL
        SELECT 'DA99', 'DA00', N'Khác'
    ) v
    LEFT JOIN (
        -- Parent lookup cũng phải bao gồm cả dữ liệu mới
        SELECT ma_nvkd, ma_ql, ten_nvkd
        FROM DMNHANVIENKD_VIEW
        
        UNION ALL
        
        SELECT 'VB99', 'VB00', N'Khác'
        UNION ALL
        SELECT 'VA99', 'TVV01', N'Khác'
        UNION ALL
        SELECT 'SF99', 'PVT04', N'Khác'
        UNION ALL
        SELECT 'DF99', 'NVD01', N'Khác'
        UNION ALL
        SELECT 'XK99', 'XK00', N'Khác'
        UNION ALL
        SELECT 'DA99', 'DA00', N'Khác'
    ) parent ON v.ma_ql = parent.ma_nvkd
    WHERE v.ma_ql IS NULL 
       OR v.ma_ql = ''
       OR parent.ma_nvkd IS NULL
    
    UNION ALL
    
    -- Recursive: Lấy nhân viên cấp dưới
    SELECT 
        e.ma_nvkd,
        e.ma_ql,
        e.ten_nvkd,
        CAST(rh.stt_nhom + '.' + e.ma_nvkd AS NVARCHAR(MAX)) AS stt_nhom,
        rh.level + 1 AS level
    FROM (
        -- Dữ liệu từ VIEW gốc
        SELECT ma_nvkd, ma_ql, ten_nvkd
        FROM DMNHANVIENKD_VIEW
        
        UNION ALL
        
        -- Thêm các dòng "Khác" mới
        SELECT 'VB99', 'VB00', N'Khác'
        UNION ALL
        SELECT 'VA99', 'TVV01', N'Khác'
        UNION ALL
        SELECT 'SF99', 'PVT04', N'Khác'
        UNION ALL
        SELECT 'DF99', 'NVD01', N'Khác'
        UNION ALL
        SELECT 'XK99', 'XK00', N'Khác'
        UNION ALL
        SELECT 'DA99', 'DA00', N'Khác'
    ) e
    INNER JOIN RecursiveHierarchy rh ON e.ma_ql = rh.ma_nvkd
)
SELECT 
    ma_nvkd,
    ten_nvkd,
    ma_ql,
    stt_nhom,
    level
FROM RecursiveHierarchy
ORDER BY stt_nhom;