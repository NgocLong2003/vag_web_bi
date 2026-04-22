import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import type { KBCRecord, MergedKBC } from './kbc-picker.types'

// ============================================================================
// useKBCPicker — stateful logic for KBC tree selection
//
// Handles:
// - Tree structure (Năm → Quý → Tháng)
// - Single-click = select 1, close
// - Checkbox = multi-select toggle
// - Merge multiple months into 1 MergedKBC
// - Auto-select current month based on [ngay_bd_thu_tien, ngay_kt_thu_tien]
// - Search/filter
// ============================================================================

const ROOT_KEY = '__ROOT__'

function iso(d: string | null | undefined): string {
  if (!d) return ''
  return String(d).substring(0, 10)
}

function minDate(arr: string[]): string | null {
  const valid = arr.filter(Boolean).sort()
  return valid[0] || null
}

function maxDate(arr: string[]): string | null {
  const valid = arr.filter(Boolean).sort()
  return valid[valid.length - 1] || null
}

function mergeKBCs(months: KBCRecord[]): MergedKBC {
  if (months.length === 1) return { ...months[0] }
  return {
    id: months[0].id,
    ten_kbc: `${months.length} kỳ`,
    loai_kbc: 'merged',
    ngay_du_no_dau_ki: minDate(months.map((k) => iso(k.ngay_du_no_dau_ki))),
    ngay_bd_xuat_ban: minDate(months.map((k) => iso(k.ngay_bd_xuat_ban))),
    ngay_kt_xuat_ban: maxDate(months.map((k) => iso(k.ngay_kt_xuat_ban))),
    ngay_bd_thu_tien: minDate(months.map((k) => iso(k.ngay_bd_thu_tien))),
    ngay_kt_thu_tien: maxDate(months.map((k) => iso(k.ngay_kt_thu_tien))),
    ngay_bd_lan_ki: minDate(months.map((k) => iso(k.ngay_bd_lan_ki))),
    ngay_kt_lan_ki: maxDate(months.map((k) => iso(k.ngay_kt_lan_ki))),
    ngay_du_no_cuoi_ki: maxDate(months.map((k) => iso(k.ngay_du_no_cuoi_ki))),
  }
}

/** Tìm kỳ Tháng mà hôm nay nằm trong [ngay_bd_thu_tien, ngay_kt_thu_tien] */
function findCurrentMonthKBC(kbcList: KBCRecord[]): KBCRecord | null {
  if (!kbcList.length) return null
  const today = new Date().toISOString().substring(0, 10)
  const months = kbcList.filter((k) => k.loai_kbc === 'Tháng')

  // Ưu tiên kỳ Tháng chứa hôm nay
  const found = months.find((k) => {
    const bd = iso(k.ngay_bd_thu_tien)
    const kt = iso(k.ngay_kt_thu_tien)
    return bd && kt && today >= bd && today <= kt
  })
  if (found) return found

  // Fallback: kỳ Tháng gần hôm nay nhất (theo ngay_kt_thu_tien ≤ today, lấy cái gần nhất)
  // Nếu không có kỳ nào trong quá khứ, lấy kỳ Tháng đầu tiên.
  const past = months
    .filter((k) => {
      const kt = iso(k.ngay_kt_thu_tien)
      return kt && kt <= today
    })
    .sort((a, b) => iso(b.ngay_kt_thu_tien).localeCompare(iso(a.ngay_kt_thu_tien)))
  if (past.length) return past[0]

  return months[0] || null
}

export function useKBCPicker(kbcList: KBCRecord[], onChange: (kbc: MergedKBC | null) => void) {
  // Build tree maps
  const { byParent, kbcMap } = useMemo(() => {
    const map: Record<number, KBCRecord> = {}
    const allIds = new Set<number>()
    const bp: Record<string, KBCRecord[]> = {}

    kbcList.forEach((k) => {
      map[k.id] = k
      allIds.add(k.id)
    })

    kbcList.forEach((k) => {
      const pid = k.parent_id && allIds.has(k.parent_id) ? String(k.parent_id) : ROOT_KEY
      if (!bp[pid]) bp[pid] = []
      bp[pid].push(k)
    })

    // Sort children
    Object.values(bp).forEach((arr) => arr.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0)))

    return { byParent: bp, kbcMap: map }
  }, [kbcList])

  // Checked set (month IDs only)
  const [checked, setChecked] = useState<Set<number>>(new Set())

  // Expanded nodes
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})

  // Flag: đã auto-select lần đầu chưa (tránh override khi user clear selection)
  const autoSelectedRef = useRef(false)

  // Search
  const [query, setQuery] = useState('')

  // ── AUTO-SELECT: chạy khi kbcList load xong ──
  useEffect(() => {
    if (autoSelectedRef.current) return
    if (!kbcList.length) return

    const found = findCurrentMonthKBC(kbcList)
    if (!found) return

    autoSelectedRef.current = true

    // Set checked
    const nextChecked = new Set([found.id])
    setChecked(nextChecked)

    // Auto-expand ancestors
    const exp: Record<number, boolean> = {}
    let pid = found.parent_id
    while (pid && kbcList.find((k) => k.id === pid)) {
      exp[pid] = true
      const parent = kbcList.find((k) => k.id === pid)
      pid = parent?.parent_id ?? null
    }
    setExpanded((prev) => ({ ...prev, ...exp }))

    // Apply ngay → trigger onChange để parent load data
    onChange(mergeKBCs([found]))
  }, [kbcList, onChange])

  // Helpers: check if all/some descendants are checked
  function getDescendantMonthIds(id: number): number[] {
    const ids: number[] = []
    function walk(pid: string) {
      const kids = byParent[pid]
      if (!kids) return
      kids.forEach((k) => {
        if (k.loai_kbc === 'Tháng') ids.push(k.id)
        walk(String(k.id))
      })
    }
    walk(String(id))
    return ids
  }

  function allChecked(id: number): boolean {
    const k = kbcMap[id]
    if (!k) return false
    if (k.loai_kbc === 'Tháng') return checked.has(id)
    const kids = byParent[String(id)]
    if (!kids?.length) return false
    return kids.every((c) => allChecked(c.id))
  }

  function someChecked(id: number): boolean {
    const k = kbcMap[id]
    if (!k) return false
    if (k.loai_kbc === 'Tháng') return checked.has(id)
    const kids = byParent[String(id)]
    if (!kids) return false
    return kids.some((c) => someChecked(c.id))
  }

  // Apply: compute merged KBC from checked set and call onChange
  const apply = useCallback(
    (newChecked: Set<number>) => {
      const months = kbcList.filter((k) => k.loai_kbc === 'Tháng' && newChecked.has(k.id))
      if (months.length === 0) {
        onChange(null)
      } else {
        onChange(mergeKBCs(months))
      }
    },
    [kbcList, onChange]
  )

  // Single click on month name → select ONLY this, apply immediately
  const selectSingle = useCallback(
    (id: number) => {
      const next = new Set([id])
      setChecked(next)
      apply(next)
    },
    [apply]
  )

  // Checkbox toggle → multi-select, do NOT auto-close
  const toggleMulti = useCallback(
    (id: number) => {
      const k = kbcMap[id]
      if (!k) return

      setChecked((prev) => {
        const next = new Set(prev)

        if (k.loai_kbc === 'Tháng') {
          if (next.has(id)) next.delete(id)
          else next.add(id)
        } else {
          // Quý/Năm: toggle all descendant months
          const isAllOn = allChecked(id)
          const descIds = getDescendantMonthIds(id)
          descIds.forEach((did) => {
            if (isAllOn) next.delete(did)
            else next.add(did)
          })
          // Auto-expand when checking parent
          if (!isAllOn) {
            setExpanded((e) => ({ ...e, [id]: true }))
          }
        }

        return next
      })
    },
    [kbcMap, byParent]
  )

  // Apply current checked set (called on close)
  const applyCurrentChecked = useCallback(() => {
    apply(checked)
  }, [apply, checked])

  // Toggle expand
  const toggleExpand = useCallback((id: number) => {
    setExpanded((e) => ({ ...e, [id]: !e[id] }))
  }, [])

  // Get display label
  const label = useMemo(() => {
    const months = kbcList.filter((k) => k.loai_kbc === 'Tháng' && checked.has(k.id))
    if (months.length === 0) return 'Chọn kỳ...'
    if (months.length === 1) return months[0].ten_kbc
    return `${months.length} kỳ`
  }, [kbcList, checked])

  // Build visible tree nodes (for rendering)
  const visibleNodes = useMemo(() => {
    const q = query.toLowerCase().trim()

    function matches(k: KBCRecord): boolean {
      if (!q) return true
      if (`${k.ten_kbc} ${k.ma_kbc}`.toLowerCase().includes(q)) return true
      const kids = byParent[String(k.id)]
      return kids?.some(matches) || false
    }

    type TreeNode = {
      kbc: KBCRecord
      depth: number
      isMonth: boolean
      hasChildren: boolean
      isExpanded: boolean
      isChecked: boolean
      isIndeterminate: boolean
      isSingleSelected: boolean
    }

    const nodes: TreeNode[] = []

    function walk(parentKey: string, depth: number) {
      const kids = byParent[parentKey]
      if (!kids) return
      kids.forEach((k) => {
        if (!matches(k)) return
        const isMonth = k.loai_kbc === 'Tháng'
        const hasChildren = !!byParent[String(k.id)]
        const isExp = q ? true : expanded[k.id] === true

        nodes.push({
          kbc: k,
          depth,
          isMonth,
          hasChildren,
          isExpanded: isExp,
          isChecked: isMonth ? checked.has(k.id) : allChecked(k.id),
          isIndeterminate: !isMonth && !allChecked(k.id) && someChecked(k.id),
          isSingleSelected: isMonth && checked.has(k.id) && checked.size === 1,
        })

        if (hasChildren && isExp) {
          walk(String(k.id), depth + 1)
        }
      })
    }

    walk(ROOT_KEY, 0)
    return nodes
  }, [kbcList, byParent, expanded, checked, query])

  return {
    visibleNodes,
    label,
    query,
    setQuery,
    selectSingle,
    toggleMulti,
    toggleExpand,
    applyCurrentChecked,
    checked,
  }
}