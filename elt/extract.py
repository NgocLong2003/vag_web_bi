"""
elt/connections.py — Connection factory cho ELT
=================================================
Một hàm duy nhất: get_ds(name) → connection object.
Tự detect type từ DATASOURCES registry trong config.py.

Usage:
    from elt.connections import get_ds

    conn = get_ds('source.asia')       # → pyodbc connection
    client = get_ds('source.cns')      # → CnsApiClient
    data_dir = get_ds('bronze.asia')   # → Path string
"""

import logging
from config import DATASOURCES

logger = logging.getLogger(__name__)


def get_config(name):
    """Lấy config dict từ registry. Raise nếu không tồn tại."""
    if name not in DATASOURCES:
        available = ', '.join(sorted(DATASOURCES.keys()))
        raise KeyError(f"Datasource '{name}' không tồn tại. Có: {available}")
    return DATASOURCES[name]


def get_ds(name):
    """
    Tạo connection/client từ datasource name.

    Returns:
        sqlserver  → pyodbc.Connection
        rest_api   → CnsApiClient (có .get(), .post())
        duckdb     → str data_dir path
    """
    config = get_config(name)
    ds_type = config['type']

    if ds_type == 'sqlserver':
        return _connect_sqlserver(config)

    elif ds_type == 'rest_api':
        return _connect_rest_api(config)

    elif ds_type == 'duckdb':
        return config['data_dir']

    else:
        raise ValueError(f"Datasource '{name}': type '{ds_type}' không được hỗ trợ")


# ═══════════════════════════════════════════════════════
# CONNECTORS
# ═══════════════════════════════════════════════════════

def _connect_sqlserver(config):
    """Tạo pyodbc connection từ config dict."""
    import pyodbc
    c = config
    conn_str = (
        f"DRIVER={{{c['driver']}}};"
        f"SERVER={c['server']},{c['port']};"
        f"DATABASE={c['database']};"
        f"UID={c['username']};PWD={c['password']};"
        "TrustServerCertificate=yes;Connect Timeout=30;"
    )
    return pyodbc.connect(conn_str, timeout=30)


def _connect_rest_api(config):
    """Tạo REST API client từ config dict."""
    import requests
    import time as _time

    class RestApiClient:
        """Generic REST API client với auto-refresh token."""

        def __init__(self, config):
            self.base_url = config['base_url']
            self.auth_url = f"{self.base_url}{config.get('auth_path', '/auth/token')}"
            self.api_url = f"{self.base_url}{config.get('api_path', '/api')}"
            self.credentials = {
                "grant_type": "password",
                "username": config['username'],
                "password": config['password'],
            }
            if config.get('client_id'):
                self.credentials['client_id'] = config['client_id']
            self.config = config
            self._token = None
            self._token_expires = 0

        def _get_token(self):
            now = _time.time()
            if self._token and now < self._token_expires:
                return self._token
            resp = requests.post(self.auth_url, data=self.credentials, headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            self._token_expires = now + data.get("expires_in", 3500) - 60
            return self._token

        def _headers(self):
            return {
                "Authorization": f"Bearer {self._get_token()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

        def get(self, endpoint, timeout=300):
            """GET request → Response JSON."""
            resp = requests.get(
                f"{self.api_url}/{endpoint}",
                headers=self._headers(), timeout=timeout
            )
            resp.raise_for_status()
            return resp.json()

        def post(self, endpoint, body, timeout=300):
            """POST request → Response JSON."""
            resp = requests.post(
                f"{self.api_url}/{endpoint}", json=body,
                headers=self._headers(), timeout=timeout
            )
            resp.raise_for_status()
            return resp.json()

    return RestApiClient(config)