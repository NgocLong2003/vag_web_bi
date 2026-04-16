"""
Báo cáo KPI — Blueprint
So sánh doanh thu/doanh số thực tế vs KPI đăng ký, hiển thị dạng tree graph.
API prefix: /reports/bao-cao-kpi/api/...
"""
from flask import Blueprint, request, render_template, current_app
from api_logger import api_response
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('bckpi', __name__,
               url_prefix='/reports/bao-cao-kpi',
               template_folder='templates')

from query_loader import load_sql

try:
    from config import SQLSERVER_CONFIG
except ImportError:
    SQLSERVER_CONFIG = None


def get_store():
    return current_app.config['DUCKDB_STORE']


def _ss_conn():
    import pyodbc
    c = SQLSERVER_CONFIG
    return pyodbc.connect(
        f"DRIVER={{{c['driver']}}};SERVER={c['server']},{c['port']};"
        f"DATABASE={c['database']};UID={c['username']};PWD={c['password']};"
        "TrustServerCertificate=yes;Connect Timeout=30;",
        autocommit=True
    )


@bp.route('/')
def index():
    from database import get_db
    db = get_db()
    kbc = db.execute('SELECT * FROM ky_bao_cao ORDER BY sort_order, id').fetchall()
    kbc_list = [dict(r) for r in kbc]
    return render_template('baocao_kpi.html', ky_bao_cao=kbc_list)


@bp.route('/api/kbc')
def api_kbc():
    """Trả về danh sách kỳ báo cáo."""
    try:
        from database import get_db
        db = get_db()
        kbc = db.execute('SELECT * FROM ky_bao_cao ORDER BY sort_order, id').fetchall()
        data = [dict(r) for r in kbc]
        return api_response(ok=True, data=data, count=len(data))
    except Exception as e:
        logger.error(f'bckpi kbc error: {e}')
        return api_response(ok=False, error=str(e))


@bp.route('/api/data')
def api_data():
    """Trả về: KPI targets (tree) + doanh thu thực tế + tháng làm việc."""
    ma_kbc_list = request.args.getlist('ma_kbc')
    ma_bp = request.args.get('ma_bp', '').strip()
    metric = request.args.get('metric', 'dt')
    scope = request.args.get('scope', 'nb')

    kbcs = []
    for k in ma_kbc_list:
        for part in k.split(','):
            part = part.strip()
            if part:
                kbcs.append(part)

    if not kbcs:
        return api_response(ok=True, nodes=[], meta={'kbcs': [], 'metric': metric})

    try:
        # ═══════════════════════════════════════════════════
        # 1. Load KPI targets from SQL Server
        # ═══════════════════════════════════════════════════
        conn = _ss_conn()
        cur = conn.cursor()
        ph = ','.join(['?'] * len(kbcs))
        sql_kpi = f"""SELECT ma_kbc, ma_nvkd, ten_nvkd, ma_ql, ma_bp, stt_nhom,
                             kpi, kpi_cong_ty, kpi_ds, kpi_ds_cong_ty
                      FROM kpi_targets WHERE ma_kbc IN ({ph})"""
        params = list(kbcs)
        if ma_bp:
            sql_kpi += ' AND ma_bp = ?'
            params.append(ma_bp)
        sql_kpi += ' ORDER BY stt_nhom, ma_nvkd'
        cur.execute(sql_kpi, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()

        # KPI field mapping
        kpi_fields = {'dt': {'nb': 'kpi', 'cty': 'kpi_cong_ty'},
                      'ds': {'nb': 'kpi_ds', 'cty': 'kpi_ds_cong_ty'}}
        kpi_field = kpi_fields.get(metric, {}).get(scope, 'kpi')
        kpi_nb_field = kpi_fields.get(metric, {}).get('nb', 'kpi')
        kpi_cty_field = kpi_fields.get(metric, {}).get('cty', 'kpi_cong_ty')

        # Build seen{} (node info) + kpi sums
        seen = {}
        kpi_sum = {}
        kpi_nb_sum = {}
        kpi_cty_sum = {}
        for r in rows:
            rd = {cols[i]: r[i] for i in range(len(cols))}
            ma = rd['ma_nvkd'] or ''
            if not ma:
                continue
            if ma not in seen:
                nv_bp = rd['ma_bp'] or ''
                nv_ql = rd['ma_ql'] or ''
                if not nv_bp:
                    nv_bp = 'XX'
                if nv_bp and not nv_ql:
                    nv_ql = nv_bp + '99'
                seen[ma] = {
                    'ma_nvkd': ma, 'ten_nvkd': rd['ten_nvkd'] or '',
                    'ma_ql': nv_ql, 'ma_bp': nv_bp,
                    'stt_nhom': rd['stt_nhom'] or '',
                }
            if ma not in kpi_sum:
                kpi_sum[ma] = 0
                kpi_nb_sum[ma] = 0
                kpi_cty_sum[ma] = 0
            kpi_sum[ma] += float(rd[kpi_field] or 0)
            kpi_nb_sum[ma] += float(rd[kpi_nb_field] or 0)
            kpi_cty_sum[ma] += float(rd[kpi_cty_field] or 0)

        # ═══════════════════════════════════════════════════
        # 2. Load cdate for "new employee" badge
        # ═══════════════════════════════════════════════════
        cdate_map = {}
        try:
            cur.execute("SELECT ma_nvkd, cdate FROM DMNHANVIENKD_VIEW WHERE ma_nvkd IS NOT NULL")
            for r in cur.fetchall():
                if r[0] and r[1]:
                    cdate_map[(r[0] or '').strip()] = r[1]
        except:
            pass

        conn.close()

        # ═══════════════════════════════════════════════════
        # 3. Load actual revenue/sales from DuckDB
        # ═══════════════════════════════════════════════════
        store = get_store()
        actual_per_nvkd = {}
        actual_per_bp = {}
        actual_bp_map = {}

        min_a = max_a = min_b = max_b = min_ds = max_ds = None

        try:
            from database import get_db
            db = get_db()
            ph_kbc = ','.join(['?' for _ in kbcs])
            kbc_rows = db.execute(
                f'''SELECT ma_kbc, ngay_bd_xuat_ban, ngay_kt_xuat_ban,
                           ngay_bd_thu_tien, ngay_kt_thu_tien
                    FROM ky_bao_cao WHERE ma_kbc IN ({ph_kbc})''',
                kbcs
            ).fetchall()

            dates_a, dates_b = [], []
            dates_ds = []
            for kr in kbc_rows:
                bd_xb = str(kr['ngay_bd_xuat_ban'] or '')[:10]
                kt_xb = str(kr['ngay_kt_xuat_ban'] or '')[:10]
                bd_tt = str(kr['ngay_bd_thu_tien'] or '')[:10]
                kt_tt = str(kr['ngay_kt_thu_tien'] or '')[:10]
                if bd_tt and kt_tt:
                    dates_a.append((bd_tt, kt_tt))
                if bd_xb and kt_xb:
                    dates_b.append((bd_xb, kt_xb))
                    dates_ds.append((bd_xb, kt_xb))

            has_dates = dates_a or dates_b or dates_ds
            if has_dates:
                min_a = min(d[0] for d in dates_a) if dates_a else None
                max_a = max(d[1] for d in dates_a) if dates_a else None
                min_b = min(d[0] for d in dates_b) if dates_b else None
                max_b = max(d[1] for d in dates_b) if dates_b else None
                min_ds = min(d[0] for d in dates_ds) if dates_ds else None
                max_ds = max(d[1] for d in dates_ds) if dates_ds else None

                if metric == 'dt' and min_a:
                    sql = load_sql('DOANHTHU_BCKPI_DUCK')
                    rows_actual = store.query(sql, [min_a, max_a, min_b, max_b, ''])
                    for r in rows_actual:
                        ma_nv = (r.get('ma_nvkd') or '').strip()
                        bp_c = (r.get('ma_bp') or '').strip()
                        val = float(r.get('doanhthu', 0) or 0)
                        if ma_nv:
                            actual_per_nvkd[ma_nv] = actual_per_nvkd.get(ma_nv, 0) + val
                            if bp_c and ma_nv not in actual_bp_map:
                                actual_bp_map[ma_nv] = bp_c

                    bp_date_cond = f"(ma_bp IN ('VA','VB','SF') AND ngay_ct >= '{min_a}' AND ngay_ct <= '{max_a}')"
                    if min_b:
                        bp_date_cond += f" OR (ma_bp NOT IN ('VA','VB','SF') AND ngay_ct >= '{min_b}' AND ngay_ct <= '{max_b}')"
                    sql_bp = f"""
                        SELECT ma_bp, SUM(ps_co) as total
                        FROM PTHUBAOCO
                        WHERE tk_co = '131' AND ma_bp != 'TN'
                          AND (
                            (ngay_ct >= '2026-01-01' AND tk_no IN ('1111','11211','11212','11213','11214','11221','1112','11215'))
                            OR (ngay_ct < '2026-01-01' AND ma_ct = 'CA1')
                          )
                          AND ({bp_date_cond})
                        GROUP BY ma_bp
                    """
                    for r in store.query(sql_bp):
                        bp_c = (r.get('ma_bp') or '').strip()
                        if bp_c:
                            actual_per_bp[bp_c] = float(r.get('total', 0) or 0)

                elif metric == 'ds' and min_ds:
                    sql = load_sql('DOANHSO_BCKPI_DUCK')
                    rows_actual = store.query(sql, [min_ds, max_ds, ''])
                    for r in rows_actual:
                        ma_nv = (r.get('ma_nvkd') or '').strip()
                        bp_c = (r.get('ma_bp') or '').strip()
                        val = float(r.get('doanhso', 0) or 0)
                        if ma_nv:
                            actual_per_nvkd[ma_nv] = actual_per_nvkd.get(ma_nv, 0) + val
                            if bp_c and ma_nv not in actual_bp_map:
                                actual_bp_map[ma_nv] = bp_c
                        if bp_c:
                            actual_per_bp[bp_c] = actual_per_bp.get(bp_c, 0) + val

        except Exception as e:
            logger.warning(f'Could not load actual revenue: {e}')

        # ═══════════════════════════════════════════════════
        # 4a. NVKD có actual nhưng không trong phân công
        # ═══════════════════════════════════════════════════
        missing_nvkds = set(actual_per_nvkd.keys()) - set(seen.keys())
        if missing_nvkds:
            ref_date = max_b or max_a or max_ds

            nv_found = {}
            if ref_date:
                try:
                    conn2 = _ss_conn()
                    cur2 = conn2.cursor()
                    ph_m = ','.join(['?' for _ in missing_nvkds])
                    cur2.execute(
                        f"""SELECT ma_nvkd, ten_nvkd, ma_ql, stt_nhom
                            FROM dim_nhanvien_history
                            WHERE ma_nvkd IN ({ph_m})
                              AND valid_from <= ?
                              AND (valid_to IS NULL OR valid_to > ?)""",
                        list(missing_nvkds) + [ref_date, ref_date])
                    for r in cur2.fetchall():
                        mx = (r[0] or '').strip()
                        if mx:
                            nv_found[mx] = {
                                'ten_nvkd': (r[1] or '').strip(),
                                'ma_ql': (r[2] or '').strip(),
                                'stt_nhom': (r[3] or '').strip(),
                            }
                    conn2.close()
                except Exception as e:
                    logger.warning(f'Could not query dim_nhanvien_history: {e}')

            khac_extra = {}
            remove_from_actual = []

            for mx in missing_nvkds:
                bp_code = actual_bp_map.get(mx, 'XX')
                if ma_bp and bp_code != ma_bp:
                    remove_from_actual.append(mx)
                    continue

                nv = nv_found.get(mx)
                if nv and nv['ma_ql'] and nv['ma_ql'] in seen:
                    seen[mx] = {
                        'ma_nvkd': mx,
                        'ten_nvkd': nv['ten_nvkd'],
                        'ma_ql': nv['ma_ql'],
                        'ma_bp': bp_code,
                        'stt_nhom': nv['stt_nhom'],
                    }
                    kpi_sum[mx] = 0
                    kpi_nb_sum[mx] = 0
                    kpi_cty_sum[mx] = 0
                else:
                    khac_node = bp_code + '99'
                    khac_extra[khac_node] = khac_extra.get(khac_node, 0) + actual_per_nvkd.get(mx, 0)
                    remove_from_actual.append(mx)

            for khac_node, val in khac_extra.items():
                actual_per_nvkd[khac_node] = actual_per_nvkd.get(khac_node, 0) + val
            for mx in remove_from_actual:
                if mx in actual_per_nvkd:
                    del actual_per_nvkd[mx]

        # ═══════════════════════════════════════════════════
        # 4b. Tree walk bottom-up → actual_node{}
        # ═══════════════════════════════════════════════════
        tree_ch = {}
        for mv, info in seen.items():
            pid = info.get('ma_ql', '')
            if not pid or pid not in seen:
                pid = '__ROOT__'
            if pid not in tree_ch:
                tree_ch[pid] = []
            tree_ch[pid].append(mv)

        actual_node = {}

        def calc_actual(mv):
            if mv in actual_node:
                return actual_node[mv]
            info = seen.get(mv, {})
            children = tree_ch.get(mv, [])
            is_company = mv == 'VAG' or (not info.get('ma_ql'))

            if not children:
                actual_node[mv] = actual_per_nvkd.get(mv, 0)
            else:
                child_sum = 0
                for c in children:
                    child_sum += calc_actual(c)

                if is_company:
                    t = sum(actual_per_bp.values())
                    actual_node[mv] = t if not ma_bp else actual_per_bp.get(ma_bp, 0)
                elif mv.endswith('00'):
                    actual_node[mv] = actual_per_bp.get(info.get('ma_bp', ''), 0)
                else:
                    actual_node[mv] = actual_per_nvkd.get(mv, 0) + child_sum

            return actual_node[mv]

        for mv in tree_ch.get('__ROOT__', []):
            calc_actual(mv)
        for mv in seen:
            if mv not in actual_node:
                calc_actual(mv)

        # ═══════════════════════════════════════════════════
        # 5. Tính months_worked cho nhân viên mới
        # ═══════════════════════════════════════════════════
        from datetime import datetime, date
        report_month = None
        for kbc in kbcs:
            try:
                parts = kbc.replace('T', '').split('-')
                report_month = date(int(parts[1]), int(parts[0]), 1)
                break
            except:
                pass

        # ═══════════════════════════════════════════════════
        # 6. Build nodes[] → return
        # ═══════════════════════════════════════════════════
        nodes = []
        for ma, info in seen.items():
            kpi_nb_val = kpi_nb_sum.get(ma, 0)
            kpi_cty_val = kpi_cty_sum.get(ma, 0)
            actual_val = actual_node.get(ma, 0)

            months_worked = None
            cdt = cdate_map.get(ma)
            if cdt and report_month:
                try:
                    if hasattr(cdt, 'year'):
                        cd = cdt
                    else:
                        cd = datetime.strptime(str(cdt)[:10], '%Y-%m-%d').date()
                    diff = (report_month.year - cd.year) * 12 + (report_month.month - cd.month)
                    if diff <= 6:
                        months_worked = max(diff, 0)
                except:
                    pass

            nodes.append({
                'ma_nvkd': ma,
                'ten_nvkd': info['ten_nvkd'],
                'ma_ql': info['ma_ql'],
                'ma_bp': info['ma_bp'],
                'stt_nhom': info['stt_nhom'],
                'kpi': kpi_nb_val,
                'kpi_cty': kpi_cty_val,
                'actual': actual_val,
                'months': months_worked,
            })

        return api_response(ok=True, nodes=nodes, count=len(nodes),
                            meta={'kbcs': kbcs, 'metric': metric, 'scope': scope, 'ma_bp': ma_bp})

    except Exception as e:
        logger.error(f'bckpi data error: {e}')
        return api_response(ok=False, error=str(e))


@bp.route('/api/detail')
def api_detail():
    """Chi tiết doanh thu/doanh số cho 1 hoặc nhiều NV."""
    ma_kbc_list = request.args.getlist('ma_kbc')
    ma_nvkd = request.args.get('ma_nvkd', '').strip()
    metric = request.args.get('metric', 'dt')
    ds_nvkd = request.args.get('ds_nvkd', '').strip()

    kbcs = []
    for k in ma_kbc_list:
        for p in k.split(','):
            p = p.strip()
            if p: kbcs.append(p)

    if not kbcs or not ds_nvkd:
        return api_response(ok=True, rows=[])

    try:
        from database import get_db
        db = get_db()
        ph_kbc = ','.join(['?' for _ in kbcs])
        kbc_rows = db.execute(
            f'''SELECT ma_kbc, ngay_bd_thu_tien, ngay_kt_thu_tien,
                       ngay_bd_xuat_ban, ngay_kt_xuat_ban
                FROM ky_bao_cao WHERE ma_kbc IN ({ph_kbc})''', kbcs
        ).fetchall()

        dates_a, dates_b, dates_ds = [], [], []
        for kr in kbc_rows:
            bd_tt = str(kr['ngay_bd_thu_tien'] or '')[:10]
            kt_tt = str(kr['ngay_kt_thu_tien'] or '')[:10]
            bd_xb = str(kr['ngay_bd_xuat_ban'] or '')[:10]
            kt_xb = str(kr['ngay_kt_xuat_ban'] or '')[:10]
            if bd_tt and kt_tt: dates_a.append((bd_tt, kt_tt))
            if bd_xb and kt_xb: dates_b.append((bd_xb, kt_xb))
            dates_ds.append((bd_xb, kt_xb))

        store = get_store()
        rows = []

        if metric == 'dt':
            if not dates_a:
                return api_response(ok=True, rows=[])
            min_a = min(d[0] for d in dates_a)
            max_a = max(d[1] for d in dates_a)
            min_b = min(d[0] for d in dates_b) if dates_b else None
            max_b = max(d[1] for d in dates_b) if dates_b else None

            sql = load_sql('DOANHTHU_BCKH_DUCK')
            result = store.query(sql, [min_a, max_a, min_b, max_b, '', ds_nvkd, ''])
            for r in result:
                rows.append({
                    'ngay_ct': str(r.get('ngay_ct', ''))[:10],
                    'ma_kh': r.get('ma_kh', ''),
                    'ma_bp': r.get('ma_bp', ''),
                    'ma_nvkd': r.get('ma_nvkd', ''),
                    'doanhthu': float(r.get('doanhthu', 0) or 0),
                })
        else:
            if not dates_ds:
                return api_response(ok=True, rows=[])
            min_ds = min(d[0] for d in dates_ds)
            max_ds = max(d[1] for d in dates_ds)

            sql = load_sql('DOANHSO_CHITIET_BCCT_DUCK')
            result = store.query(sql, [min_ds, max_ds, '', ds_nvkd, ''])
            for r in result:
                rows.append({
                    'ngay_ct': str(r.get('ngay_ct', ''))[:10],
                    'ma_kh': r.get('ma_kh', ''),
                    'ma_vt': r.get('ma_vt', ''),
                    'ten_vt': r.get('ten_vt', ''),
                    'dvt': r.get('dvt', ''),
                    'so_luong': float(r.get('so_luong', 0) or 0),
                    'doanhso': float(r.get('doanhso', 0) or 0),
                    'ma_nvkd': r.get('ma_nvkd', ''),
                    'ma_bp': r.get('ma_bp', ''),
                })

        return api_response(ok=True, rows=rows,
                            meta={'kbcs': kbcs, 'metric': metric, 'ma_nvkd': ma_nvkd})

    except Exception as e:
        logger.error(f'bckpi detail error: {e}')
        return api_response(ok=False, error=str(e))