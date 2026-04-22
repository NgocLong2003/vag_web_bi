import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useAuth } from '@shared/auth/AuthProvider'
import { useReportStore } from '@shared/stores/useReportStore'
import { BPSlicerStrip } from '@shared/ui/slicers/BPSlicerStrip'
import { KBCPicker } from '@shared/ui/slicers/KBCPicker'
import type { KBCRecord, MergedKBC } from '@shared/ui/slicers/kbc-picker.types'
import { useHierarchy } from '../../shared/hooks/useHierarchy'
import { computeAllowedNV, getAllowedBP, parseList } from '../../shared/utils/permissions'
import { fmtNumber as fmtV, fmtDate as fmtD, numHTML, shimmerHTML, escHtml as escHTML } from '@shared/utils/format'
import { useKhachHangData } from './useKhachHangData'
import { COLUMN_IDS, buildDisplayColumns, computeDates } from './columns'
import type { NVNode, FlatRow, ColumnDef, KyBaoCao } from '../../shared/components/TreeTable/types'

const API_BASE = '/reports/bao-cao-khach-hang'

/** Map MergedKBC → KyBaoCao (cùng shape, chỉ khác tên type) */
function toKyBaoCao(m: MergedKBC): KyBaoCao {
  return {
    id: m.id,
    ten_kbc: m.ten_kbc,
    loai: m.loai_kbc,
    nam: 0, // không cần
    ngay_du_no_dau_ki: m.ngay_du_no_dau_ki || '',
    ngay_bd_xuat_ban: m.ngay_bd_xuat_ban || '',
    ngay_kt_xuat_ban: m.ngay_kt_xuat_ban || '',
    ngay_bd_thu_tien: m.ngay_bd_thu_tien || '',
    ngay_kt_thu_tien: m.ngay_kt_thu_tien || '',
    ngay_bd_lan_ki: m.ngay_bd_lan_ki || '',
    ngay_kt_lan_ki: m.ngay_kt_lan_ki || '',
    ngay_du_no_cuoi_ki: m.ngay_du_no_cuoi_ki || '',
  }
}

export default function KhachHangPage() {
  const { user } = useAuth()

  // ── User permissions ──
  const userNvkdList = useMemo(() => {
    const raw = user?.maNvkdList
    if (Array.isArray(raw)) return raw.filter(Boolean)
    if (typeof raw === 'string') return parseList(raw)
    return []
  }, [user])
  const userBpList = useMemo(() => {
    const raw = (user as any)?.maBp || (user as any)?.ma_bp || ''
    if (Array.isArray(raw)) return raw.filter(Boolean)
    if (typeof raw === 'string') return parseList(raw)
    return []
  }, [user])

  // ── Hierarchy ──
  const hier = useHierarchy(API_BASE)

  // ── Data loader ──
  const dataLoader = useKhachHangData()

  // ── State ──
  const [kbcList, setKbcList] = useState<KBCRecord[]>([])
  const [currentKBC, setCurrentKBC] = useState<MergedKBC | null>(null)
  const [selectedBP, setSelectedBP] = useState('')
  const [ttSplit, setTtSplit] = useState(false)
  const [expState, setExpState] = useState<Record<string, boolean>>({})
  const [allExp, setAllExp] = useState(true)
  const [initDone, setInitDone] = useState(false)
  const [dataLoading, setDataLoading] = useState(false)
  const [dataError, setDataError] = useState('')

  // ── Computed ──
  const allowedNV = useMemo(() => {
    if (!hier.hierarchy.length) return new Set<string>()
    return computeAllowedNV(hier.hierarchy, userNvkdList)
  }, [hier.hierarchy, userNvkdList])

  const allowedBP = useMemo(() => {
    return getAllowedBP(userBpList, hier.khMap)
  }, [userBpList, hier.khMap])

  const kbc = useMemo(() => currentKBC ? toKyBaoCao(currentKBC) : null, [currentKBC])

  // ── Init ──
  useEffect(() => {
    async function init() {
      const result = await hier.load()
      if (!result) return
      try {
        const res = await fetch(API_BASE + '/api/ky-bao-cao').then(r => r.json())
        if (res.success && res.data.length) setKbcList(res.data)
      } catch { /* bỏ qua */ }
      const exp: Record<string, boolean> = {}
      result.hierarchy.forEach((h: any) => { exp[h.ma_nvkd] = true }) // mặc định mở hết
      setExpState(exp)
      setAllExp(true)
      setInitDone(true)
    }
    init()
  }, []) // eslint-disable-line

  // ── Load data khi KBC hoặc BP thay đổi ──
  useEffect(() => {
    if (!kbc || !hier.hierarchy.length || !initDone) return
    let cancelled = false
    async function loadData() {
      setDataLoading(true)
      setDataError('')
      try {
        dataLoader.reset([...COLUMN_IDS])
        await dataLoader.loadAllData(kbc!, selectedBP, allowedNV, userNvkdList, userBpList, hier.khMap, null)
        if (!cancelled) dataLoader.aggregate(hier.nvMap, hier.hierarchy, [...COLUMN_IDS])
      } catch (e: any) {
        if (!cancelled) setDataError(e.message || 'Lỗi tải dữ liệu')
      } finally {
        if (!cancelled) setDataLoading(false)
      }
    }
    loadData()
    return () => { cancelled = true }
  }, [kbc, selectedBP, initDone]) // eslint-disable-line

  // ── Display columns ──
  const displayCols = useMemo(() => {
    if (!kbc) return []
    return buildDisplayColumns(kbc, ttSplit, selectedBP)
  }, [kbc, ttSplit, selectedBP])

  // ── Flat rows ──
  const flatRows = useMemo(() => {
    if (!hier.hierarchy.length || !kbc) return []
    dataLoader.aggregate(hier.nvMap, hier.hierarchy, [...COLUMN_IDS])
    return buildFlatRows(hier, expState, allowedNV, userNvkdList, null, [...COLUMN_IDS])
  }, [hier.hierarchy, hier.nvMap, expState, allowedNV, dataLoader.columns, kbc])

  // ── Handlers ──
  function toggleNV(id: string) { setExpState(p => ({ ...p, [id]: !p[id] })) }
  useEffect(() => { (window as any).__togNV = toggleNV; return () => { delete (window as any).__togNV } })

  // ── Refs ──
  const wrapRef = useRef<HTMLDivElement>(null)
  const theadRef = useRef<HTMLTableSectionElement>(null)

  // Measure thead height
  useEffect(() => {
    if (!theadRef.current || !wrapRef.current) return
    const h = theadRef.current.getBoundingClientRect().height
    wrapRef.current.style.setProperty('--thead-h', `${h}px`)
  }, [flatRows, displayCols])

  // ── Scroll handler: hide stale sticky NV rows from wrong branches ──
useEffect(() => {
  const wrap = wrapRef.current
  const thead = theadRef.current
  if (!wrap || !thead) return

  let ticking = false
  function onScroll() {
    if (ticking) return
    ticking = true
    requestAnimationFrame(() => {
      ticking = false

      const allNV = wrap!.querySelectorAll<HTMLTableRowElement>('tr.row-nv.row-sticky')

      // Reset toàn bộ trạng thái
      allNV.forEach(r => {
  const el = r as HTMLElement
  el.classList.remove('sticky-hidden')
})
      void wrap!.offsetHeight

      const wrapRect = wrap!.getBoundingClientRect()

      // Bước 1: active NV tại mỗi depth - cái này quan trọng, đừng sửa. Sửa là nó bị hiện ông này trong slot ông kia, nhìn rất sai.
      const activeByDepth = new Map<number, HTMLTableRowElement>()
      allNV.forEach(r => {
        const rect = r.getBoundingClientRect()
        const depth = parseInt(r.dataset.depth || '0')
        const stickyTopPx = parseFloat(getComputedStyle(r).top) || 0
        const stickyY = wrapRect.top + stickyTopPx
        if (rect.top <= stickyY + 1) {
          activeByDepth.set(depth, r)
        }
      })

      // Bước 2: build chain hợp lệ
      const sortedDepths = [...activeByDepth.keys()].sort((a, b) => a - b)
      const validIds = new Set<string>()
      const chainIds: string[] = []
      for (const d of sortedDepths) {
        const r = activeByDepth.get(d)!
        const ancStr = r.dataset.ancestors || ''
        const ancestors = ancStr ? ancStr.split('|').filter(Boolean) : []
        const match = ancestors.length === chainIds.length &&
          ancestors.every((a, i) => a === chainIds[i])
        if (!match) break
        chainIds.push(r.dataset.id || '')
        validIds.add(r.dataset.id || '')
      }

      // Bước 3: ẩn NV đã qua slot mà không thuộc chain
      allNV.forEach(r => {
        const id = r.dataset.id || ''
        if (validIds.has(id)) return
        const rect = r.getBoundingClientRect()
        const stickyTopPx = parseFloat(getComputedStyle(r).top) || 0
        const stickyY = wrapRect.top + stickyTopPx
        if (rect.top <= stickyY + 1) {
          r.classList.add('sticky-hidden')
        }
      })

      // Bước 4: đẩy NV cuối chain xuống theo KH nếu KH chưa xuống đủ
const wrapRectForPush = wrap!.getBoundingClientRect()

// Build map id → NV một lần (tránh find() nhiều lần)
const nvById = new Map<string, HTMLTableRowElement>()
allNV.forEach(r => { nvById.set(r.dataset.id || '', r) })

const lastId = chainIds[chainIds.length - 1]
const lastNV = lastId ? nvById.get(lastId) : null

// Tập KH thuộc NV cuối chain
const activeKHSet = new Set<HTMLElement>()
if (lastNV) {
  let c: Element | null = lastNV.nextElementSibling
  while (c && c.classList.contains('row-kh')) {
    activeKHSet.add(c as HTMLElement)
    c = c.nextElementSibling
  }
}

// Clear padding cho KH không thuộc active
wrap!.querySelectorAll<HTMLTableRowElement>('tr.row-kh').forEach(r => {
  if (activeKHSet.has(r)) return
  r.querySelectorAll<HTMLElement>('td').forEach(td => {
    if (td.style.paddingTop) td.style.paddingTop = ''
    if (td.style.height) td.style.height = ''
  })
})

// Push KH đầu xuống
if (lastNV) {
  const nvRect = lastNV.getBoundingClientRect()
  const nvBottom = nvRect.top + nvRect.height

  let cur: Element | null = lastNV.nextElementSibling
  while (cur && cur.classList.contains('row-kh')) {
    const khEl = cur as HTMLElement
    const khOffsetTop = khEl.offsetTop
    const khNaturalY = khOffsetTop - wrap!.scrollTop + wrapRectForPush.top
    const overlap = nvBottom - khNaturalY
    if (overlap <= 0) {
      khEl.querySelectorAll<HTMLElement>('td').forEach(td => {
        if (td.style.paddingTop) td.style.paddingTop = ''
        if (td.style.height) td.style.height = ''
      })
      break
    }
    const cappedOverlap = Math.round(Math.min(overlap, 200) / 8) * 8
    const newHeight = `${34 + cappedOverlap}px`
const newPad = `${cappedOverlap}px`
khEl.querySelectorAll<HTMLElement>('td').forEach(td => {
  const curPad = parseFloat(td.style.paddingTop) || 0
  if (Math.abs(curPad - cappedOverlap) > 8) {
    td.style.height = newHeight
    td.style.paddingTop = newPad
  }
})
    break
  }
}
    })
  }

  wrap.addEventListener('scroll', onScroll, { passive: true })
  onScroll()
  return () => wrap.removeEventListener('scroll', onScroll)
}, [flatRows])

  function toggleAllExp() {
    const next = !allExp; setAllExp(next)
    const exp: Record<string, boolean> = {}
    hier.hierarchy.forEach(h => { exp[h.ma_nvkd] = next })
    setExpState(exp)
  }

  /** Column resize grip — drag to resize first column */
  function startResize(e: React.MouseEvent) {
    e.preventDefault(); e.stopPropagation()
    const th = (e.target as HTMLElement).parentElement!
    const startX = e.clientX, startW = th.offsetWidth
    const grip = e.target as HTMLElement
    grip.classList.add('active')
    function onMove(ev: MouseEvent) {
      const nw = Math.max(160, startW + (ev.clientX - startX))
      th.style.width = nw + 'px'
      th.style.minWidth = nw + 'px'
    }
    function onUp() {
      grip.classList.remove('active')
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  // ── Register report metadata + download handler in store ──
  const setDownloadHandler = useReportStore((s: any) => s.setDownloadHandler)
  const setDownloading = useReportStore((s: any) => s.setDownloading)
  const setReportName = useReportStore((s: any) => s.setReportName)
  const setUpdateMode = useReportStore((s: any) => s.setUpdateMode)
  const setUpdateInterval = useReportStore((s: any) => s.setUpdateInterval)
  const setLastUpdateText = useReportStore((s: any) => s.setLastUpdateText)
  const setStoreDashboards = useReportStore((s: any) => s.setDashboards)
  const clearReport = useReportStore((s: any) => s.clearReport)

  // Set report name + update mode on mount
  useEffect(() => {
    // Load dashboard list → find this report's metadata
    fetch('/api/dashboards').then(r => r.json()).then(res => {
      if (!res.success) return
      setStoreDashboards(res.data)
      // Tìm dashboard hiện tại theo slug
      const current = res.data.find((d: any) => d.slug === 'bao-cao-khach-hang')
      if (current) {
        setReportName(current.name || 'Báo cáo Khách hàng')
        setUpdateMode(current.update_mode === 'realtime' ? 'realtime' : 'scheduled')
        if (current.update_interval) setUpdateInterval(current.update_interval)
        if (current.updated_at) {
          // Tính thời gian tương đối
          const diff = Date.now() - new Date(current.updated_at).getTime()
          const m = Math.floor(diff / 60000)
          if (m < 1) setLastUpdateText('Vừa cập nhật')
          else if (m < 60) setLastUpdateText(`${m} phút trước`)
          else if (m < 1440) setLastUpdateText(`${Math.floor(m / 60)} giờ trước`)
          else setLastUpdateText(`${Math.floor(m / 1440)} ngày trước`)
        }
      } else {
        setReportName('Báo cáo Khách hàng')
        setUpdateMode('realtime')
      }
    }).catch(() => {
      setReportName('Báo cáo Khách hàng')
      setUpdateMode('realtime')
    })
    return () => clearReport()
  }, []) // eslint-disable-line

  const handleDownload = useCallback(async (_format: string) => {
    if (!flatRows.length || !kbc) return
    setDownloading(true)
    try {
      const dates = computeDates(kbc)
      const dispCols = buildDisplayColumns(kbc, ttSplit, selectedBP)
      const colHeaderMap: Record<string, string> = {
        du_no_dk: `DƯ NỢ ĐẦU THÁNG\nADMIN chốt số ${fmtD(dates.ngayDNDKPlus1)}`,
        ban_ra: `BÁN RA\n${fmtD(dates.dBDXB)} → ${fmtD(dates.dKTXB)}`,
        tt1: `THANH TOÁN\n${fmtD(dates.dBDTT)} → ${fmtD(dates.ngayTruocLK)}`,
        tt2: `THANH TOÁN\n${fmtD(dates.dBDLK)} → ${fmtD(dates.dKTTT)}`,
        tt_merged: `THANH TOÁN\n${fmtD(dates.dBDTT)} → ${fmtD(dates.dKTTT)}`,
        du_no_tk: `DƯ NỢ CẦN THU\nTRONG KỲ`,
        du_no_ct: `DƯ NỢ CUỐI THÁNG\nADMIN chốt số ${fmtD(dates.dDNCK)}`,
        du_no_ck: `DƯ NỢ CUỐI KỲ\nSau TT tới ${fmtD(dates.dKTTT)}`,
      }
      const colHeaders = dispCols.map(c => colHeaderMap[c.id] || c.label)

      // Build payload rows
      const payload: any[] = []
      flatRows.forEach(row => {
        if (row.type === 'nv' && row.node) {
          payload.push({
            type: 'nv', depth: row.depth,
            name: row.node.ten_nvkd || row.node.ma_nvkd,
            values: dispCols.map(c => dataLoader.getCellNV(row.node!, c.id)),
          })
        } else if (row.type === 'kh' && row.parentNV) {
          payload.push({
            type: 'kh', depth: 0,
            name: row.tenKH || row.maKH,
            values: dispCols.map(c => dataLoader.getCellKH(row.parentNV!, row.maKH!, c.id)),
          })
        }
      })

      // Total row
      let roots: NVNode[]
      if (userNvkdList.length) {
        roots = userNvkdList.filter(id => hier.nvMap.has(id)).map(id => hier.nvMap.get(id)!)
      } else {
        roots = hier.hierarchy.filter(h => !h.ma_ql || !hier.nvMap.has(h.ma_ql))
      }
      payload.push({
        type: 'total', depth: 0, name: 'TỔNG CỘNG',
        values: dispCols.map(c => {
          let sum = 0, has = false
          roots.forEach(r => { const t = dataLoader.getCellNV(r, c.id); if (t != null) { sum += t; has = true } })
          return has ? sum : null
        }),
      })

      // POST to Flask API → download blob
      const resp = await fetch(API_BASE + '/api/export_excel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows: payload, col_headers: colHeaders, kbc_name: kbc.ten_kbc || '' }),
      })
      if (!resp.ok) throw new Error('Lỗi server ' + resp.status)
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const cd = resp.headers.get('Content-Disposition')
      let fn = `BaoCaoKH_${kbc.ten_kbc || ''}.xlsx`
      if (cd) { const m = cd.match(/filename=(.+)/); if (m) fn = m[1].replace(/"/g, '') }
      a.download = fn
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      console.error('Export error:', e)
    } finally {
      setDownloading(false)
    }
  }, [flatRows, kbc, ttSplit, selectedBP, dataLoader, hier, userNvkdList, setDownloading])

  useEffect(() => {
    setDownloadHandler(handleDownload)
  }, [handleDownload]) // eslint-disable-line

  // ── Render ──
  const isLoading = hier.loading || (!initDone && !hier.error)
  const errorMsg = hier.error || dataError
  const emptyMsg = !kbc ? 'Chưa chọn kỳ báo cáo'
    : (initDone && !dataLoading && flatRows.length === 0 && !errorMsg) ? 'Không có dữ liệu cho kỳ này' : undefined

  return (
    <div className="rpt-page">
      {/* BP Slicer Strip — floating, cùng z với header */}
      {allowedBP.length > 0 && (
        <div className="bp-header-strip">
          <BPSlicerStrip value={selectedBP} onChange={setSelectedBP} allowedBPs={allowedBP} />
        </div>
      )}

      {/* Slicer bar — floating, centered, dưới header dropdowns */}
      <div className="rpt-slicer-bar">
        <KBCPicker kbcList={kbcList} value={currentKBC} onChange={setCurrentKBC} />

        {dataLoading && (
          <>
            <span className="rpt-vdiv" />
            <div className="rpt-status">
              <span className="rpt-status-dot busy" />
              <span>Đang tải...</span>
            </div>
          </>
        )}

        <span className="rpt-vdiv" />

        <button className="rpt-btn" onClick={toggleAllExp}>
          <svg viewBox="0 0 16 16"><polyline points={allExp ? '4,10 8,6 12,10' : '4,6 8,10 12,6'} /></svg>
          {allExp ? 'Thu gọn' : 'Mở rộng'}
        </button>
      </div>

      {/* Content */}
      <div className="rpt-content">
        {isLoading ? (
          <div className="rpt-state">
            <div className="rpt-spinner" />
            <span>Đang tải dữ liệu…</span>
          </div>
        ) : errorMsg ? (
          <div className="rpt-state rpt-state-err">⚠ {errorMsg}</div>
        ) : emptyMsg ? (
          <div className="rpt-state">{emptyMsg}</div>
        ) : flatRows.length > 0 && displayCols.length > 0 ? (
          <div className="tt-wrap" ref={wrapRef}>
            <table className="tt-table">
              <thead ref={theadRef}>
                <tr>
                  <th style={{ textAlign: 'left', minWidth: 220 }}>
                    NV / Khách hàng
                    <div className="col-grip" onMouseDown={startResize} />
                  </th>
                  <th style={{ textAlign: 'left', minWidth: 60, width: 70 }}>Mã</th>
                  {displayCols.map(col => {
                    const isTT = col.id === 'tt_merged' || col.id === 'tt1'
                    return (
                      <th key={col.id} className={col.className} style={{ minWidth: col.minWidth }}>
                        <div className="tt-th-main">
                          {col.label}
                          {isTT && (
                            <button className="tt-split-btn" onClick={() => setTtSplit(!ttSplit)}>
                              {ttSplit ? '⟨ Gộp ⟩' : '⟩ Tách ⟨'}
                            </button>
                          )}
                        </div>
                        {col.subLabel && (
                          <div className="tt-th-date">
                            {col.subLabel.split('\n').map((l, i) => <span key={i}>{l}<br /></span>)}
                          </div>
                        )}
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody dangerouslySetInnerHTML={{
                __html: renderBody(flatRows, displayCols, dataLoader, hier.khNames),
              }} />
              <tfoot>
                <tr>
                  <td><span className="foot-lbl">Tổng cộng</span></td>
                  <td></td>
                  {displayCols.map(col => (
                    <td key={col.id} style={{ textAlign: 'right' }}
                      dangerouslySetInnerHTML={{
                        __html: renderFooterCell(col, hier, dataLoader, userNvkdList),
                      }}
                    />
                  ))}
                </tr>
              </tfoot>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════
// BUILD FLAT ROWS
// ═══════════════════════════════════════════════════════════════

function buildFlatRows(
  hier: ReturnType<typeof useHierarchy>,
  expState: Record<string, boolean>,
  allowedNV: Set<string>,
  userNvkdList: string[],
  selectedKH: string | null,
  colIds: string[],
): FlatRow[] {
  const rows: FlatRow[] = []
  const { nvMap, hierarchy } = hier

  function hasData(nd: NVNode): boolean {
    if (!allowedNV.has(nd.ma_nvkd)) return false
    for (const c of colIds) {
      const cv = nd._vals[c]
      if (cv && cv.total != null && cv.total !== 0) return true
    }
    return nd.children.some(c => hasData(c))
  }

  function getKHKeys(nd: NVNode): string[] {
    const s = new Set<string>()
    colIds.forEach(c => {
      if (nd._vals[c]) Object.keys(nd._vals[c].kh).forEach(k => s.add(k))
    })
    let keys = [...s]
    if (selectedKH) keys = keys.filter(k => k === selectedKH)
    return keys
  }

  let roots: NVNode[]
  if (userNvkdList.length) {
    roots = userNvkdList.filter(id => nvMap.has(id)).map(id => nvMap.get(id)!)
  } else {
    roots = hierarchy.filter(h => !h.ma_ql || !nvMap.has(h.ma_ql))
  }
  roots.sort((a, b) => a.stt_nhom.localeCompare(b.stt_nhom))
  const visRoots = roots.filter(r => hasData(r))
  const baseLevel = visRoots.length ? Math.min(...visRoots.map(r => r.level)) : 0

  function walk(
  nd: NVNode,
  ancestors: { cont: boolean }[],
  isLast: boolean,
  ancestorIds: string[],
) {
  if (!hasData(nd)) return
  const fk = getKHKeys(nd)
  const vc = [...nd.children].sort((a, b) => a.stt_nhom.localeCompare(b.stt_nhom)).filter(c => hasData(c))
  const depth = nd.level - baseLevel
  const expanded = expState[nd.ma_nvkd] !== false

  rows.push({
    type: 'nv', node: nd, expanded,
    hasKids: vc.length > 0 || fk.length > 0,
    depth, ancestors: [...ancestors], isLast,
    ancestorIds: [...ancestorIds],
  })

  if (expanded) {
    const total = fk.length + vc.length
    let idx = 0
    const nextAncestors = [...ancestorIds, nd.ma_nvkd]
    fk.forEach(k => {
      const il = idx === total - 1
      rows.push({
        type: 'kh', maKH: k, tenKH: hier.khNames.get(k) || k,
        parentNV: nd, depth: depth + 1,
        ancestors: [...ancestors, { cont: !il }], isLast: il,
      })
      idx++
    })
    vc.forEach(child => {
      const il = idx === total - 1
      walk(child, [...ancestors, { cont: !il }], il, nextAncestors)
      idx++
    })
  }
}

visRoots.forEach((r, ri) => walk(r, [], ri === visRoots.length - 1, []))
  return rows
}


// ═══════════════════════════════════════════════════════════════
// RENDER HELPERS (string HTML for performance)
// ═══════════════════════════════════════════════════════════════

function renderBody(
  rows: FlatRow[],
  cols: ColumnDef[],
  data: ReturnType<typeof useKhachHangData>,
  khNames: Map<string, string>,
): string {
  let html = ''
  const INDENT = 24
  const ROW_H = 34

  rows.forEach((row, rowIdx) => {
    if (row.type === 'nv' && row.node) {
  const nd = row.node
  const lv = 'lv' + Math.min(row.depth, 5)
  const indent = row.depth * INDENT
  const togSvg = row.expanded ? '<path d="M1.5 3L4.5 6.5L7.5 3"/>' : '<path d="M3 1.5L6.5 4.5L3 7.5"/>'
  const tog = row.hasKids
    ? `<button class="tog" onclick="window.__togNV&&window.__togNV('${nd.ma_nvkd}')"><svg viewBox="0 0 9 9">${togSvg}</svg></button>`
    : '<span class="tog-sp"></span>'

  const stickyTop = row.depth * ROW_H
  const stickyStyle = `--sticky-top:calc(var(--thead-h, 70px) + ${stickyTop}px)`

  const treeHtml = row.depth > 0 ? buildTreeLines(row, INDENT) : ''

  // THÊM: attribute cho scroll handler
  const ancAttr = (row.ancestorIds || []).join('|')
  const idAttr = escHTML(nd.ma_nvkd)

  let tds = ''
  cols.forEach(col => {
    if (data.isLoading(col.id)) { tds += `<td style="text-align:right">${shimmerHTML()}</td>`; return }
    const v = data.getCellNV(nd, col.id)
    if (data.isLoaded(col.id)) {
      tds += `<td style="text-align:right">${v != null ? numHTML(v, 'sub', !!col.isInverse) : '<span class="n zero">0</span>'}</td>`
    } else {
      tds += '<td style="text-align:right"><span class="dash">—</span></td>'
    }
  })
  html += `<tr class="row-nv ${lv} row-sticky" style="${stickyStyle}" data-depth="${row.depth}" data-id="${idAttr}" data-ancestors="${escHTML(ancAttr)}"><td class="td-tree">${treeHtml}<div class="cell-name"><span class="cell-spacer" style="width:${indent}px"></span><div class="cell-block ${lv}">${tog}<span class="nametxt">${escHTML(nd.ten_nvkd || nd.ma_nvkd)}</span></div></div></td><td><span class="code">${escHTML(nd.ma_nvkd)}</span></td>${tds}</tr>`
    } else if (row.type === 'kh' && row.parentNV) {
      const mk = row.maKH!
      const indent = row.depth * INDENT
      const passLines = buildPassthroughLines(row, INDENT)

      let tds = ''
      cols.forEach(col => {
        if (data.isLoading(col.id)) { tds += `<td style="text-align:right">${shimmerHTML()}</td>`; return }
        const v = data.getCellKH(row.parentNV!, mk, col.id)
        if (data.isLoaded(col.id)) {
          tds += `<td style="text-align:right">${v != null ? numHTML(v, '', !!col.isInverse) : '<span class="n zero">0</span>'}</td>`
        } else {
          tds += '<td style="text-align:right"><span class="dash">—</span></td>'
        }
      })
      html += `<tr class="row-kh"><td class="td-tree">${passLines}<div class="cell-name"><span class="cell-spacer" style="width:${indent}px"></span><div class="cell-block kh"><span class="tog-sp"></span><span class="nametxt">${escHTML(row.tenKH || mk)}</span></div></div></td><td><span class="code" style="font-size:9px;color:var(--g4)">${escHTML(mk)}</span></td>${tds}</tr>`
    }
  })
  return html
}

/**
 * Vẽ tree lines trong cell-spacer (position:relative).
 * X của toggle tại depth d = d * INDENT + 9px (giữa slot 24px).
 *
 * - tl-v: đường dọc full height tại ancestor X (ancestor còn sibling)
 * - tl-v tl-half: đường dọc nửa trên (last child — L-shape)
 * - tl-h: đường ngang từ parent X tới cell-block
 */
function buildTreeLines(row: FlatRow, INDENT: number): string {
  if (row.depth <= 0) return ''
  let lines = ''
  const parentX = (row.depth - 1) * INDENT + 9

  // Đường dọc xuyên suốt cho ancestors còn sibling bên dưới
  row.ancestors.forEach((anc, i) => {
    if (anc.cont) {
      const x = i * INDENT + 9
      lines += `<span class="tl-v" style="left:${x}px"></span>`
    }
  })

  // Hook dọc: last child = nửa trên, not last = full
  if (row.isLast) {
    lines += `<span class="tl-v tl-half" style="left:${parentX}px"></span>`
  } else {
    lines += `<span class="tl-v" style="left:${parentX}px"></span>`
  }

  // Hook ngang: từ parentX tới cell-block
  const hookW = row.depth * INDENT - parentX
  if (hookW > 0) {
    lines += `<span class="tl-h" style="left:${parentX}px;width:${hookW}px"></span>`
  }

  return lines
}

/** KH rows: chỉ vẽ đường dọc xuyên suốt của ancestors NV, không vẽ hook */
function buildPassthroughLines(row: FlatRow, INDENT: number): string {
  let lines = ''
  // Chỉ vẽ vlines cho NV ancestors còn sibling — bỏ qua ancestor cuối (NV→KH)
  row.ancestors.forEach((anc, i) => {
    if (i >= row.depth - 1) return // bỏ ancestor cuối (là NV cha trực tiếp → KH)
    if (anc.cont) {
      const x = i * INDENT + 9
      lines += `<span class="tl-v" style="left:${x}px"></span>`
    }
  })
  return lines
}

function renderFooterCell(
  col: ColumnDef,
  hier: ReturnType<typeof useHierarchy>,
  data: ReturnType<typeof useKhachHangData>,
  userNvkdList: string[],
): string {
  if (!data.isLoaded(col.id)) return '<span class="n grand">—</span>'
  let roots: NVNode[]
  if (userNvkdList.length) {
    roots = userNvkdList.filter(id => hier.nvMap.has(id)).map(id => hier.nvMap.get(id)!)
  } else {
    roots = hier.hierarchy.filter(h => !h.ma_ql || !hier.nvMap.has(h.ma_ql))
  }
  let sum = 0, has = false
  roots.forEach(r => {
    const t = data.getCellNV(r, col.id)
    if (t != null) { sum += t; has = true }
  })
  return `<span class="n grand">${has ? fmtV(sum) : '—'}</span>`
}