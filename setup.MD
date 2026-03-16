# Hướng dẫn chạy VietAnh BI trên máy nội bộ (SQL Server)

## Bước 1: Cài đặt môi trường

```bash
# Cài Python 3.9+ (nếu chưa có)
# Download: https://www.python.org/downloads/

# Cài thư viện
pip install flask pyodbc
```

### Cài ODBC Driver cho SQL Server (bắt buộc)
- Download: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
- Chọn "ODBC Driver 17 for SQL Server" hoặc "ODBC Driver 18 for SQL Server"
- Cài xong kiểm tra:
```bash
# Windows: mở ODBC Data Sources → tab Drivers → phải thấy "ODBC Driver 17 for SQL Server"
# Hoặc chạy:
python -c "import pyodbc; print(pyodbc.drivers())"
```

## Bước 2: Tạo Database trên SQL Server

1. Mở **SQL Server Management Studio (SSMS)**
2. Kết nối đến SQL Server instance
3. Mở file `setup_sqlserver.sql` → Execute
4. Kiểm tra database `VietAnhBI` đã được tạo

## Bước 3: Cấu hình flask_app.py

Mở `flask_app.py`, chỉnh phần CẤU HÌNH:

```python
# Đổi sang SQL Server
DB_TYPE = 'sqlserver'

# Chỉnh thông tin kết nối
SQLSERVER_CONFIG = {
    'server': 'localhost',              # hoặc tên instance: 'DESKTOP-ABC\\SQLEXPRESS'
    'port': '1433',                     # port mặc định
    'database': 'VietAnhBI',
    'username': 'sa',                   # tài khoản SQL Server
    'password': 'MatKhauCuaBan',        # password
    'driver': 'ODBC Driver 17 for SQL Server',
}
```

### Lưu ý nếu dùng SQL Server Express:
- Server name có thể là: `localhost\\SQLEXPRESS` hoặc `.\\SQLEXPRESS`
- Cần bật TCP/IP trong SQL Server Configuration Manager
- Port mặc định có thể khác 1433 → kiểm tra trong Configuration Manager

### Lưu ý nếu dùng Windows Authentication:
Đổi connection string trong hàm `_get_sqlserver_conn()`:
```python
conn_str = (
    f"DRIVER={{{cfg['driver']}}};"
    f"SERVER={cfg['server']};"
    f"DATABASE={cfg['database']};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)
```

## Bước 4: Chạy app

```bash
cd /path/to/vietanhbi
python flask_app.py
```

Mở trình duyệt: **http://localhost:5000**

Đăng nhập: `admin` / `vietanh@2026`

## Bước 5: Cho người khác trong mạng LAN truy cập

```bash
# Chạy app listen trên tất cả interface:
python -c "from flask_app import app; app.run(host='0.0.0.0', port=5000)"
```

Người khác truy cập: **http://IP_MÁY_BẠN:5000**

VD: http://192.168.1.100:5000

### Mở firewall Windows:
1. Mở Windows Firewall → Advanced Settings
2. Inbound Rules → New Rule → Port → TCP 5000 → Allow

## Chuyển đổi giữa SQLite và SQL Server

Chỉ cần đổi 1 dòng trong `flask_app.py`:

```python
DB_TYPE = 'sqlite'      # ← dùng khi deploy PythonAnywhere
DB_TYPE = 'sqlserver'   # ← dùng khi chạy nội bộ
```

Code, templates, logic hoàn toàn giống nhau — không cần sửa gì khác.

## Cấu trúc file

```
vietanhbi/
├── flask_app.py              ← App chính
├── setup_sqlserver.sql       ← Script tạo DB trên SQL Server
├── requirements.txt          ← Thư viện Python
├── data.db                   ← SQLite DB (tự tạo khi DB_TYPE='sqlite')
├── SETUP_LOCAL.md            ← File hướng dẫn này
└── templates/
    ├── login.html
    ├── dashboard.html
    ├── dashboard_list.html
    ├── admin.html
    ├── admin_permissions.html
    ├── analytics.html
    └── settings.html
```