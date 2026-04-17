"""
api_logger.py — Ghi log mọi API call kèm kết quả chi tiết
==========================================================
Cách dùng:
    1. Import và gắn middleware vào app:
        from api_logger import init_api_logger
        init_api_logger(app)

    2. Trong route, dùng api_response() thay cho jsonify():
        from api_logger import api_response
        return api_response(ok=True, rows=rows)            # tự đếm row_count
        return api_response(ok=False, error='Lỗi XYZ')     # ghi lỗi
        return api_response(ok=True, rows=rows, meta={'ma_vt': 'NL001'})  # kèm context

    3. Với route trả file (send_file), gắn thủ công:
        from api_logger import set_api_result
        set_api_result(status='ok', row_count=len(rows), meta={'export': filename})
        return send_file(...)

Bảng SQL Server: xem CREATE TABLE ở cuối file.
"""
from flask import g, request, session, jsonify
from datetime import datetime
import time
import json
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# 1. Helper: api_response() — thay thế jsonify() cho API
# ═══════════════════════════════════════════════════════

def api_response(ok=True, rows=None, error=None, meta=None, status_code=None, **kwargs):
    """
    Wrapper jsonify() tự gắn g.api_result để middleware ghi log.

    Params:
        ok          : True/False
        rows        : list of dicts (nếu có, tự đếm row_count)
        error       : str mô tả lỗi (nếu có)
        meta        : dict context bổ sung (ma_vt, ngay, ...)
        status_code : HTTP status (mặc định 200 nếu ok, 500 nếu error)
        **kwargs    : thêm field vào JSON response (count, elapsed_ms, message, ...)

    Returns:
        Flask Response (jsonify)
    """
    # Build response body — giữ cả 'ok' lẫn 'success' cho backward compatibility
    body = {'ok': ok, 'success': ok}
    if rows is not None:
        body['rows'] = rows
        body['count'] = len(rows)
    if error is not None:
        body['error'] = error
    body.update(kwargs)

    # Gắn result vào g để middleware đọc
    result = {
        'status': 'ok' if ok else 'error',
        'row_count': len(rows) if rows is not None else kwargs.get('count'),
        'error': error,
    }
    if meta:
        result['meta'] = meta
    g.api_result = result

    # HTTP status
    if status_code is None:
        status_code = 200 if ok else 500

    resp = jsonify(body)
    resp.status_code = status_code
    return resp


def set_api_result(status='ok', row_count=None, error=None, meta=None):
    """
    Gắn g.api_result thủ công — dùng cho route trả send_file hoặc
    response đặc biệt không qua api_response().
    """
    g.api_result = {
        'status': status,
        'row_count': row_count,
        'error': error,
        'meta': meta,
    }


# ═══════════════════════════════════════════════════════
# 2. Middleware: init_api_logger(app)
# ═══════════════════════════════════════════════════════

def init_api_logger(app, ds_name='default'):
    """
    Gắn before_request + after_request để tự động log API calls.

    Params:
        app     : Flask app
        ds_name : datasource để ghi log (mặc định 'default')
    """

    @app.before_request
    def _api_log_start():
        # Chỉ track /reports/.../api/...
        if '/api/' in request.path and request.path.startswith('/reports/'):
            g.api_start = time.perf_counter()

    @app.after_request
    def _api_log_write(response):
        start = getattr(g, 'api_start', None)
        if start is None:
            return response

        elapsed_ms = round((time.perf_counter() - start) * 1000)
        result = getattr(g, 'api_result', None) or {}

        # Xác định status
        status = result.get('status')
        if not status:
            status = 'ok' if response.status_code < 400 else 'error'

        # User info từ session
        user_id = session.get('user_id')
        user_name = session.get('username')

        # Params — GET query string + POST JSON body
        params = dict(request.args)
        if request.method in ('POST', 'PUT', 'PATCH'):
            try:
                body = request.get_json(silent=True)
                if body and isinstance(body, dict):
                    # Chỉ lấy scalar params, bỏ list/dict lớn (như rows export)
                    for k, v in body.items():
                        if isinstance(v, (str, int, float, bool)) or v is None:
                            params[k] = v
            except Exception:
                pass
        for k in ('password', 'token', 'secret', 'rows', 'col_headers'):
            params.pop(k, None)

        # Meta — context bổ sung từ route
        meta = result.get('meta')

        # Report — tự đọc từ blueprint.api_report nếu có
        report_name = None
        if request.blueprints:
            bp_obj = app.blueprints.get(request.blueprints[0])
            if bp_obj:
                report_name = getattr(bp_obj, 'api_report', None)

        # Report session — frontend gửi qua header, nhóm các API cùng 1 lần thao tác
        report_session = request.headers.get('X-Report-Session')

        record = {
            'user_id': user_id,
            'user_name': user_name,
            'report': report_name,
            'report_session': report_session,
            'endpoint': request.path,
            'method': request.method,
            'params': json.dumps(params, ensure_ascii=False) if params else None,
            'http_status': response.status_code,
            'status': status,
            'row_count': result.get('row_count'),
            'error': result.get('error'),
            'elapsed_ms': elapsed_ms,
            'ip': request.headers.get('X-Real-IP', request.remote_addr),
            'user_agent': _parse_ua(str(request.user_agent)),
            'meta': json.dumps(meta, ensure_ascii=False) if meta else None,
        }

        # Ghi async-safe: bắn vào queue hoặc ghi trực tiếp
        # Hiện tại ghi trực tiếp — nếu cần performance hơn, đổi sang queue
        try:
            _write_log(record, ds_name)
        except Exception as e:
            # Log ghi thất bại không được block response
            logger.warning(f'[api_logger] write failed: {e}')

        return response


import re

# ═══════════════════════════════════════════════════════
# UA parser — không cần thư viện ngoài
# ═══════════════════════════════════════════════════════

def _parse_ua(ua_string):
    """
    Parse raw user-agent → dạng ngắn gọn.
    'Mozilla/5.0 (Windows NT 10.0; ...) Chrome/127.0.0.0 ...'
    → 'Chrome 127 / Windows 10'
    """
    if not ua_string:
        return 'Unknown'

    # ── Detect browser ──
    browser = 'Unknown'
    # Thứ tự quan trọng: check cụ thể trước, generic sau
    patterns = [
        (r'Edg[eA]?/(\d+)',        'Edge'),
        (r'OPR/(\d+)',             'Opera'),
        (r'Brave/(\d+)',           'Brave'),
        (r'Vivaldi/(\d+)',         'Vivaldi'),
        (r'CriOS/(\d+)',           'Chrome iOS'),
        (r'FxiOS/(\d+)',           'Firefox iOS'),
        (r'SamsungBrowser/(\d+)',   'Samsung'),
        (r'UCBrowser/(\d+)',        'UC Browser'),
        (r'Chrome/(\d+)',          'Chrome'),
        (r'Firefox/(\d+)',         'Firefox'),
        (r'Version/(\d+).*Safari', 'Safari'),
        (r'Safari/(\d+)',          'Safari'),
    ]
    for pat, name in patterns:
        m = re.search(pat, ua_string)
        if m:
            browser = f'{name} {m.group(1)}'
            break

    # ── Detect OS ──
    os_name = 'Unknown'
    if 'Windows NT 10' in ua_string:
        os_name = 'Windows 10/11'
    elif 'Windows NT 6.3' in ua_string:
        os_name = 'Windows 8.1'
    elif 'Windows NT 6.1' in ua_string:
        os_name = 'Windows 7'
    elif 'Windows' in ua_string:
        os_name = 'Windows'
    elif 'iPhone' in ua_string:
        os_name = 'iPhone'
    elif 'iPad' in ua_string:
        os_name = 'iPad'
    elif 'Android' in ua_string:
        m = re.search(r'Android (\d+)', ua_string)
        os_name = f'Android {m.group(1)}' if m else 'Android'
    elif 'Mac OS X' in ua_string:
        os_name = 'macOS'
    elif 'Linux' in ua_string:
        os_name = 'Linux'
    elif 'CrOS' in ua_string:
        os_name = 'ChromeOS'

    # ── Detect device type ──
    is_mobile = any(k in ua_string for k in ('Mobile', 'Android', 'iPhone', 'iPad'))
    device = 'Mobile' if is_mobile else 'PC'

    return f'{browser} / {os_name} / {device}'


def _write_log(record, ds_name='warehouse'):
    """Ghi 1 record vào bảng api_access_log.
    Dùng query() vì SQLServerDataSource không có execute().
    autocommit=True nên INSERT qua query() vẫn commit bình thường.
    """
    from datasource import get_ds
    ds = get_ds(ds_name)

    sql = """
        SET NOCOUNT ON;
        INSERT INTO api_access_log
            (user_id, user_name, report, report_session, endpoint, method, params,
             http_status, status, row_count, error,
             elapsed_ms, ip, user_agent, meta, created_at)
        VALUES
            (?, ?, ?, ?, ?, ?, ?,
             ?, ?, ?, ?,
             ?, ?, ?, ?, GETDATE())
    """
    ds.query(sql, [
        record['user_id'],
        record['user_name'],
        record['report'],
        record['report_session'],
        record['endpoint'],
        record['method'],
        record['params'],
        record['http_status'],
        record['status'],
        record['row_count'],
        record['error'],
        record['elapsed_ms'],
        record['ip'],
        record['user_agent'],
        record['meta'],
    ])


# ═══════════════════════════════════════════════════════
# 3. SQL: Tạo bảng (chạy 1 lần trên SQL Server)
# ═══════════════════════════════════════════════════════
CREATE_TABLE_SQL = """
CREATE TABLE api_access_log (
    id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id         NVARCHAR(50)   NULL,
    user_name       NVARCHAR(100)  NULL,
    report          NVARCHAR(100)  NULL,
    report_session  VARCHAR(36)    NULL,       -- nhóm các API cùng 1 lần thao tác
    endpoint        NVARCHAR(300)  NOT NULL,
    method          VARCHAR(10)    NOT NULL DEFAULT 'GET',
    params          NVARCHAR(MAX)  NULL,
    http_status     SMALLINT       NOT NULL DEFAULT 200,
    status          VARCHAR(20)    NOT NULL,
    row_count       INT            NULL,
    error           NVARCHAR(MAX)  NULL,
    elapsed_ms      INT            NULL,
    ip              VARCHAR(45)    NULL,
    user_agent      NVARCHAR(500)  NULL,
    meta            NVARCHAR(MAX)  NULL,
    created_at      DATETIME2      NOT NULL DEFAULT GETDATE(),

    INDEX IX_api_log_user     (user_id, created_at DESC),
    INDEX IX_api_log_report   (report, created_at DESC),
    INDEX IX_api_log_session  (report_session),
    INDEX IX_api_log_endpoint (endpoint, created_at DESC),
    INDEX IX_api_log_status   (status, created_at DESC),
    INDEX IX_api_log_date     (created_at DESC)
);
"""

# Nếu bảng đã tồn tại, chạy lệnh này để thêm cột:
ALTER_ADD_COLUMNS = """
ALTER TABLE api_access_log ADD report NVARCHAR(100) NULL;
ALTER TABLE api_access_log ADD report_session VARCHAR(36) NULL;
CREATE INDEX IX_api_log_report ON api_access_log (report, created_at DESC);
CREATE INDEX IX_api_log_session ON api_access_log (report_session);
"""