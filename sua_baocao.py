"""
Chạy: python patch_baocao_kd.py
Sửa templates/baocao_kinhdoanh/baocao_kd.html
CHỈ thêm API_BASE + shared header, KHÔNG đụng topbar gốc.
"""
import os

FILE = os.path.join('templates', 'baocao_kinhdoanh', 'baocao_kd.html')

if not os.path.exists(FILE):
    print(f'[ERROR] Không tìm thấy: {FILE}')
    print('Copy file index.html gốc vào đường dẫn trên trước.')
    exit(1)

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

if 'API_BASE' in content:
    print('[SKIP] File đã được patch.')
    exit(0)

count = 0

# 1. Thêm API_BASE sau "let colIdCounter=3;"
old = 'let colIdCounter=3;'
new = 'let colIdCounter=3;\nconst API_BASE="/reports/bao-cao-kinh-doanh";'
if old in content:
    content = content.replace(old, new, 1); count += 1; print('[OK] Thêm API_BASE')

# 2. Fix fetch('/api/hierarchy') và fetch('/api/khachhang')
for api in ['hierarchy', 'khachhang']:
    o = f"fetch('/api/{api}')"
    n = f"fetch(API_BASE+'/api/{api}')"
    if o in content:
        content = content.replace(o, n); count += 1; print(f'[OK] Fix fetch {api}')

# 3. Fix loadColumn() fetch
old = "var r=await fetch(url,{"
new = "var r=await fetch(API_BASE+url,{"
if old in content:
    content = content.replace(old, new, 1); count += 1; print('[OK] Fix loadColumn fetch')

# 4. Fix exportExcel() fetch
old = "fetch('/api/export_excel',{"
new = "fetch(API_BASE+'/api/export_excel',{"
if old in content:
    content = content.replace(old, new, 1); count += 1; print('[OK] Fix exportExcel fetch')

# 5. Thêm shared header CSS trước </head>
if '_header_css' not in content:
    content = content.replace('</head>',
        '{% include "_header_css.html" %}\n</head>', 1)
    count += 1; print('[OK] Thêm header CSS')

# 6. Thêm shared header HTML ngay sau <body>, TRƯỚC topbar gốc
if '_header.html' not in content:
    content = content.replace('<div class="app">',
        '{% include "_header.html" %}\n<div class="app">', 1)
    count += 1; print('[OK] Thêm shared header trước app')

# 7. Thêm header JS trước </body>
if '_header_js' not in content:
    content = content.replace('</body>',
        '{% include "_header_js.html" %}\n</body>', 1)
    count += 1; print('[OK] Thêm header JS')

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\n[DONE] Đã sửa {count} chỗ. Topbar gốc giữ nguyên.')