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
    dashboard_type NVARCHAR(50) DEFAULT 'powerbi',  -- 'powerbi' hoặc 'analytics'
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

PRINT N'Database VietAnhBI OK';
GO