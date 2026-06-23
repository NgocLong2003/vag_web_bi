"""
datasource/__init__.py — DataSource factory.

Usage:
    from datasource import get_ds
    ds = get_ds('default')       # → DuckDB (batch)
    ds = get_ds('production')    # → SQL Server (realtime)
    rows = ds.query("SELECT ...", [param1])
"""
import logging

logger = logging.getLogger(__name__)

# Singleton registry: name → DataSource instance
_instances = {}


def init_datasources(app_config, duckdb_store=None):
    """Khởi tạo tất cả datasources từ config.
    Gọi 1 lần khi app start.

    Args:
        app_config: dict DATASOURCES từ config.py
        duckdb_store: DuckDBStore instance (cho 'default')
    """
    for name, cfg in app_config.items():
        ds_type = cfg.get('type', '')

        try:
            if ds_type == 'duckdb':
                if duckdb_store:
                    from datasource.duckdb_ds import DuckDBDataSource
                    _instances[name] = DuckDBDataSource(duckdb_store)
                    logger.info(f"[DataSource] '{name}' → DuckDB (Parquet)")
                else:
                    logger.warning(f"[DataSource] '{name}' → DuckDB but no store provided")

            elif ds_type == 'sqlserver':
                from datasource.sqlserver_ds import SQLServerDataSource
                pool_size = cfg.get('pool_size', 3)
                _instances[name] = SQLServerDataSource(cfg, pool_size=pool_size)
                logger.info(f"[DataSource] '{name}' → SQL Server {cfg['server']}:{cfg['port']}/{cfg['database']}")

            else:
                logger.warning(f"[DataSource] '{name}' → Unknown type '{ds_type}', skipped")
        except Exception as e:
            logger.error(f"[DataSource] '{name}' init failed: {e}")


def get_ds(name='default'):
    """Lấy DataSource instance theo tên.

    Args:
        name: tên datasource ('default', 'production', ...)

    Returns:
        DataSource instance

    Raises:
        KeyError nếu datasource chưa được init
    """
    if name not in _instances:
        raise KeyError(f"DataSource '{name}' chưa được khởi tạo. "
                        f"Có: {list(_instances.keys())}")
    return _instances[name]


def get_all_status():
    """Trả về status tất cả datasources."""
    return {name: ds.status() for name, ds in _instances.items()}


def close_all():
    """Đóng tất cả datasources."""
    for name, ds in _instances.items():
        if hasattr(ds, 'close'):
            try:
                ds.close()
            except:
                pass
    _instances.clear()