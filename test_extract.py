"""
test_extract.py — Test extract layer
======================================
Đọc config từ config.py → DATASOURCES. Không hardcode.

    python test_extract.py asia
    python test_extract.py cns-dims
    python test_extract.py cns-cuoiky
    python test_extract.py cns-facts
    python test_extract.py cns
    python test_extract.py all
"""

import sys, os, json, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from elt.extract.base import fmt_dur


def test_asia():
    from config import DATASOURCES
    from elt.extract.asia import extract_asia
    src = DATASOURCES['source.asia']
    print("=" * 60)
    print(f"  TEST: extract/asia")
    print(f"  Source: {src['server']}:{src['port']} / {src['database']}")
    print(f"  Target: {DATASOURCES['bronze.asia']['data_dir']}")
    print("=" * 60)
    t0 = time.time()
    results = extract_asia()
    print_results("ASIA", results, time.time() - t0)
    verify_output(DATASOURCES['bronze.asia']['data_dir'])


def test_cns_dims():
    from config import DATASOURCES
    from elt.extract.cns import extract_cns_dims
    src = DATASOURCES['source.cns']
    print("=" * 60)
    print(f"  TEST: extract/cns — dims")
    print(f"  API: {src['base_url']}")
    print("=" * 60)
    t0 = time.time()
    results = extract_cns_dims()
    print_results("CNS DIMS", results, time.time() - t0)
    verify_output(DATASOURCES['bronze.cns']['data_dir'])


def test_cns_cuoiky():
    from elt.extract.cns import extract_cns_cuoiky
    print("=" * 60)
    print("  TEST: extract/cns — cuoiky sensor")
    print("=" * 60)
    t0 = time.time()
    result, changed = extract_cns_cuoiky()
    print(f"\n  Changed: {changed}")
    print_results("CNS CUOIKY", [result], time.time() - t0)


def test_cns_facts():
    from config import DATASOURCES
    from elt.extract.cns import extract_cns_facts
    from elt.extract.base import current_month_range
    tu, den = current_month_range()
    print("=" * 60)
    print(f"  TEST: extract/cns — facts ({tu} → {den})")
    print("=" * 60)
    t0 = time.time()
    results = extract_cns_facts(tu, den)
    print_results("CNS FACTS", results, time.time() - t0)
    verify_output(DATASOURCES['bronze.cns']['data_dir'])


def test_cns_all():
    from config import DATASOURCES
    from elt.extract.cns import extract_cns_all
    print("=" * 60)
    print("  TEST: extract/cns — FULL (~22 phút)")
    print("=" * 60)
    t0 = time.time()
    results, changed = extract_cns_all()
    print(f"\n  CuoiKy changed: {changed}")
    print_results("CNS ALL", results, time.time() - t0)
    verify_output(DATASOURCES['bronze.cns']['data_dir'])


# ═══════════════════════════════════════════════════════

def print_results(label, results, elapsed):
    ok = err = rows = 0
    print(f"\n  ┌─ {label} ──────────────────────────────────────┐")
    for r in results:
        icon = "✓" if r.status == 'ok' else "✗"
        extra = ""
        if r.changes:
            c = r.changes
            p = []
            if c.get("added"):   p.append(f"+{c['added']}")
            if c.get("updated"): p.append(f"~{c['updated']}")
            if c.get("deleted"): p.append(f"-{c['deleted']}")
            if p: extra = f" ({', '.join(p)})"
        if r.error: extra = f" ✗ {r.error[:50]}"
        print(f"  │ {icon} {r.table:<28} {r.rows:>8,} dòng  {fmt_dur(r.seconds):>8}{extra}")
        rows += r.rows
        if r.status == 'ok': ok += 1
        else: err += 1
    print(f"  ├─────────────────────────────────────────────────┤")
    print(f"  │ {ok} OK, {err} lỗi, {rows:,} dòng, {fmt_dur(elapsed)}")
    print(f"  └─────────────────────────────────────────────────┘")


def verify_output(data_dir):
    d = Path(data_dir)
    if not d.exists():
        print(f"\n  ⚠ {d} chưa tồn tại")
        return
    print(f"\n  ┌─ FILES ──────────────────────────────────────────┐")
    total = 0
    for root, _, files in os.walk(d):
        for f in sorted(files):
            fp = Path(root) / f
            sz = fp.stat().st_size
            total += sz
            rel = fp.relative_to(d)
            s = f"{sz/1048576:.1f} MB" if sz > 1048576 else f"{sz/1024:.0f} KB"
            print(f"  │ {str(rel):<42} {s:>8}")
    print(f"  │ {'Tổng:':<42} {total/1048576:.1f} MB")
    print(f"  └─────────────────────────────────────────────────┘")

    cs = d / "_meta" / "checksums.json"
    if cs.exists():
        print(f"\n  ┌─ CHECKSUMS ─────────────────────────────────────┐")
        with open(cs) as f:
            data = json.load(f)
        for name, info in data.items():
            ch = "⚡" if info.get("hash_changed") else "─"
            rows = info.get("row_count", 0)
            changes = info.get("changes", {})
            c_str = ""
            if changes:
                p = []
                if changes.get("added"):   p.append(f"+{changes['added']}")
                if changes.get("updated"): p.append(f"~{changes['updated']}")
                if changes.get("deleted"): p.append(f"-{changes['deleted']}")
                if p: c_str = f" ({', '.join(p)})"
            print(f"  │ {ch} {name:<30} {rows:>8,}{c_str}")
        print(f"  └─────────────────────────────────────────────────┘")


def test_transform():
    from elt.transform.base import run_transforms
    from config import DATASOURCES
    print("=" * 60)
    print(f"  TEST: transform → silver (Delta Lake)")
    print(f"  Bronze: {DATASOURCES['bronze.asia']['data_dir']}")
    print(f"  Silver: {DATASOURCES['silver']['data_dir']}")
    print("=" * 60)
    t0 = time.time()
    results = run_transforms()
    # Show Delta versions
    silver_dir = Path(DATASOURCES['silver']['data_dir'])
    if silver_dir.exists():
        print(f"\n  ┌─ SILVER TABLES ─────────────────────────────────┐")
        for d in sorted(silver_dir.iterdir()):
            if d.is_dir() and (d / '_delta_log').exists():
                from deltalake import DeltaTable
                dt = DeltaTable(str(d))
                files = dt.file_uris()
                total_size = sum(Path(f).stat().st_size for f in files)
                s = f"{total_size/1048576:.1f} MB" if total_size > 1048576 else f"{total_size/1024:.0f} KB"
                print(f"  │ {d.name:<30} v{dt.version():<4} {s:>8}")
        print(f"  └─────────────────────────────────────────────────┘")


def test_pipeline():
    from elt.pipeline import run_pipeline
    print("=" * 60)
    print("  TEST: full pipeline (extract → transform)")
    print("=" * 60)
    result = run_pipeline()
    print(f"\n  Status: {result['status']}, Total: {result['seconds']:.1f}s")


COMMANDS = {
    'asia': test_asia,
    'cns': test_cns_all,
    'cns-dims': test_cns_dims,
    'cns-cuoiky': test_cns_cuoiky,
    'cns-facts': test_cns_facts,
    'transform': test_transform,
    'pipeline': test_pipeline,
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in {*COMMANDS, 'all'}:
        print("Cách dùng:")
        for k in COMMANDS: print(f"  python test_extract.py {k}")
        print("  python test_extract.py all")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'all':
        for n, fn in COMMANDS.items():
            if n not in ('cns', 'pipeline'):
                fn()
                print()
    else:
        COMMANDS[cmd]()