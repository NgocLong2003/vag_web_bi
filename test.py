from duckdb_store import DuckDBStore
store = DuckDBStore('data/silver')
store.load()
rows = store.query('''
    SELECT ngay_ct, ma_kh_ct, ma_bp, ma_nvkd, ps_co
    FROM PTHUBAOCO
    WHERE ma_bp = 'TN'
    ORDER BY ngay_ct
    LIMIT 10
''')
for r in rows:
    print(f"  {r['ngay_ct'][:10]}  {r['ma_kh_ct']:<10} {r['ma_bp']:<6} {r['ma_nvkd']:<10} {r['ps_co']:>14,.0f}")
