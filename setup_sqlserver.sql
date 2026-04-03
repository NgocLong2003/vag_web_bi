IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'VietAnhBI')
    CREATE DATABASE VietAnhBI;
GO
USE VietAnhBI;
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'users')
CREATE TABLE users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(100) NOT NULL UNIQUE,
    password_hash NVARCHAR(200) NOT NULL,
    password_plain NVARCHAR(200) DEFAULT '',
    display_name NVARCHAR(200) DEFAULT '',
    khoi NVARCHAR(200) DEFAULT '',
    bo_phan NVARCHAR(200) DEFAULT '',
    chuc_vu NVARCHAR(200) DEFAULT '',
    ma_nvkd_list NVARCHAR(MAX) DEFAULT '',
    email NVARCHAR(200) DEFAULT '',
    ma_bp NVARCHAR(MAX) DEFAULT '',
    role NVARCHAR(20) DEFAULT 'user',
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE(),
    last_login DATETIME NULL
);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dashboards')
CREATE TABLE dashboards (
    id INT IDENTITY(1,1) PRIMARY KEY,
    slug NVARCHAR(200) NOT NULL UNIQUE,
    name NVARCHAR(200) NOT NULL,
    powerbi_url NVARCHAR(2000) DEFAULT '',
    description NVARCHAR(500) DEFAULT '',
    dashboard_type NVARCHAR(50) DEFAULT 'powerbi',  -- 'powerbi', 'analytics', 'report'
    is_active BIT DEFAULT 1,
    sort_order INT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'user_dashboards')
CREATE TABLE user_dashboards (
    user_id INT NOT NULL,
    dashboard_id INT NOT NULL,
    PRIMARY KEY (user_id, dashboard_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (dashboard_id) REFERENCES dashboards(id) ON DELETE CASCADE
);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'activity_log')
BEGIN
    CREATE TABLE activity_log (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL,
        action NVARCHAR(50) NOT NULL,
        dashboard_id INT NULL,
        ip NVARCHAR(50) DEFAULT '',
        user_agent NVARCHAR(500) DEFAULT '',
        created_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX idx_activity_created ON activity_log(created_at);
    CREATE INDEX idx_activity_user ON activity_log(user_id);
END
GO

-- Migration: thêm dashboard_type nếu bảng cũ chưa có
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('dashboards') AND name = 'dashboard_type')
    ALTER TABLE dashboards ADD dashboard_type NVARCHAR(50) DEFAULT 'powerbi';
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = 'ma_nvkd_list')
    ALTER TABLE users ADD ma_nvkd_list NVARCHAR(MAX) DEFAULT '';
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = 'email')
    ALTER TABLE users ADD email NVARCHAR(200) DEFAULT '';
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = 'ma_bp')
    ALTER TABLE users ADD ma_bp NVARCHAR(MAX) DEFAULT '';
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ky_bao_cao')
CREATE TABLE ky_bao_cao (
    id INT IDENTITY(1,1) PRIMARY KEY,
    ma_kbc NVARCHAR(50) NOT NULL UNIQUE,
    ten_kbc NVARCHAR(200) NOT NULL,
    loai_kbc NVARCHAR(20) NOT NULL,
    ngay_bd_xuat_ban DATE NOT NULL,
    ngay_kt_xuat_ban DATE NOT NULL,
    ngay_bd_thu_tien DATE NOT NULL,
    ngay_kt_thu_tien DATE NOT NULL,
    ngay_bd_lan_ki DATE NOT NULL,
    ngay_kt_lan_ki DATE NOT NULL,
    ngay_du_no_dau_ki DATE NOT NULL,
    ngay_du_no_cuoi_ki DATE NOT NULL
);
GO

-- Migration: thêm cột mới nếu bảng cũ chưa có
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'ky_bao_cao')
    AND NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ky_bao_cao') AND name = 'ngay_bd_lan_ki')
BEGIN
    ALTER TABLE ky_bao_cao ADD ngay_bd_lan_ki DATE NULL;
    ALTER TABLE ky_bao_cao ADD ngay_kt_lan_ki DATE NULL;
END
GO

PRINT N'Database VietAnhBI OK';
GO


IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'user_audit_log')
CREATE TABLE user_audit_log (
    id INT IDENTITY(1,1) PRIMARY KEY,
    target_user_id INT NOT NULL,          -- user bị sửa
    target_username NVARCHAR(100) DEFAULT '',
    changed_by_id INT NOT NULL,           -- admin đã sửa
    changed_by_username NVARCHAR(100) DEFAULT '',
    action NVARCHAR(20) NOT NULL,         -- 'create', 'edit', 'delete', 'perm_change', 'bp_change'
    changes NVARCHAR(MAX) DEFAULT '',     -- JSON mô tả thay đổi: {"field": {"old": "x", "new": "y"}, ...}
    created_at DATETIME DEFAULT GETDATE()
);
GO
 
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_audit_target')
    CREATE INDEX idx_audit_target ON user_audit_log(target_user_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_audit_changed_by')
    CREATE INDEX idx_audit_changed_by ON user_audit_log(changed_by_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_audit_created')
    CREATE INDEX idx_audit_created ON user_audit_log(created_at);
GO
 
PRINT N'user_audit_log OK';
GO