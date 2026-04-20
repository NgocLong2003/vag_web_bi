// ============================================================================
// useColumnLoader — Lazy load từng cột dữ liệu + aggregate lên cây NV
//
// Mỗi cột gọi 1 API riêng, parse response → { maNVKD: { maKH: value } }
// Sau đó aggregate: duyệt từ lá → gốc, cộng dồn total
// ============================================================================

import { useState, useCallback, useRef } from 'react'
import type { NVNode, ColumnLoadState } from '../components/TreeTable/types'

interface ColumnLoaderReturn {
  /** State loading/loaded/data của từng cột */
  columns: Record<string, ColumnLoadState>
  /** Load 1 cột: gọi fetchFn, parse, lưu vào state */
  loadColumn: (colId: string, fetchFn: () => Promise<Record<string, Record<string, number>>>) => Promise<void>
  /** Load tất cả cột cùng lúc */
  loadAll: (fetchers: Record<string, () => Promise<Record<string, Record<string, number>>>>) => Promise<void>
  /** Aggregate dữ liệu lên cây NV */
  aggregate: (nvMap: Map<string, NVNode>, hierarchy: NVNode[], colIds: string[]) => void
  /** Reset tất cả */
  reset: (colIds: string[]) => void
  /** Lấy giá trị 1 ô (NV + cột) */
  getCellNV: (node: NVNode, colId: string) => number | null
  /** Lấy giá trị 1 ô (KH + NV + cột) */
  getCellKH: (parentNV: NVNode, maKH: string, colId: string) => number | null
  /** Cột đang loading? */
  isLoading: (colId: string) => boolean
  /** Cột đã load xong? */
  isLoaded: (colId: string) => boolean
}

export function useColumnLoader(): ColumnLoaderReturn {
  const [columns, setColumns] = useState<Record<string, ColumnLoadState>>({})
  const colRef = useRef(columns)
  colRef.current = columns

  const reset = useCallback((colIds: string[]) => {
    const init: Record<string, ColumnLoadState> = {}
    colIds.forEach(id => {
      init[id] = { loading: false, loaded: false, data: {} }
    })
    setColumns(init)
  }, [])

  const loadColumn = useCallback(async (
    colId: string,
    fetchFn: () => Promise<Record<string, Record<string, number>>>,
  ) => {
    setColumns(prev => ({
      ...prev,
      [colId]: { ...prev[colId], loading: true, loaded: false },
    }))
    try {
      const data = await fetchFn()
      setColumns(prev => ({
        ...prev,
        [colId]: { loading: false, loaded: true, data },
      }))
    } catch (e) {
      console.error(`[ColumnLoader] Lỗi cột ${colId}:`, e)
      setColumns(prev => ({
        ...prev,
        [colId]: { ...prev[colId], loading: false },
      }))
    }
  }, [])

  const loadAll = useCallback(async (
    fetchers: Record<string, () => Promise<Record<string, Record<string, number>>>>,
  ) => {
    // Set tất cả loading
    setColumns(prev => {
      const next = { ...prev }
      Object.keys(fetchers).forEach(id => {
        next[id] = { loading: true, loaded: false, data: {} }
      })
      return next
    })

    // Fetch song song
    const entries = Object.entries(fetchers)
    const results = await Promise.allSettled(
      entries.map(([, fn]) => fn()),
    )

    // Cập nhật state
    setColumns(prev => {
      const next = { ...prev }
      entries.forEach(([id], i) => {
        const result = results[i]
        if (result.status === 'fulfilled') {
          next[id] = { loading: false, loaded: true, data: result.value }
        } else {
          console.error(`[ColumnLoader] Lỗi cột ${id}:`, result.reason)
          next[id] = { ...next[id], loading: false }
        }
      })
      return next
    })
  }, [])

  /** Aggregate dữ liệu lên cây: duyệt từ lá → gốc */
  const aggregate = useCallback((
    nvMap: Map<string, NVNode>,
    hierarchy: NVNode[],
    colIds: string[],
  ) => {
    const cols = colRef.current

    // Reset _vals
    nvMap.forEach(n => { n._vals = {} })

    colIds.forEach(colId => {
      const col = cols[colId]
      if (!col?.loaded) return

      // Khởi tạo _vals cho mọi node
      nvMap.forEach(n => {
        n._vals[colId] = { kh: {}, total: null }
      })

      // Gán data KH vào node
      Object.entries(col.data).forEach(([maNvkd, khData]) => {
        const nd = nvMap.get(maNvkd)
        if (!nd) return
        Object.entries(khData).forEach(([maKH, value]) => {
          nd._vals[colId].kh[maKH] = (nd._vals[colId].kh[maKH] || 0) + value
        })
      })

      // Aggregate từ lá → gốc (sort by level DESC)
      const sorted = [...hierarchy].sort((a, b) => b.level - a.level)
      sorted.forEach(h => {
        const nd = nvMap.get(h.ma_nvkd)
        if (!nd) return
        const cv = nd._vals[colId]
        let sum = 0
        let has = false

        // Cộng KH trực tiếp
        Object.values(cv.kh).forEach(v => { sum += v; has = true })

        // Cộng total của con
        nd.children.forEach(c => {
          const ct = c._vals[colId]?.total
          if (ct != null) { sum += ct; has = true }
        })

        cv.total = has ? sum : null
      })
    })
  }, [])

  const getCellNV = useCallback((node: NVNode, colId: string): number | null => {
    return node._vals[colId]?.total ?? null
  }, [])

  const getCellKH = useCallback((parentNV: NVNode, maKH: string, colId: string): number | null => {
    const cv = parentNV._vals[colId]
    if (!cv) return null
    return cv.kh[maKH] ?? null
  }, [])

  const isLoading = useCallback((colId: string): boolean => {
    return colRef.current[colId]?.loading ?? false
  }, [])

  const isLoaded = useCallback((colId: string): boolean => {
    return colRef.current[colId]?.loaded ?? false
  }, [])

  return {
    columns, loadColumn, loadAll, aggregate, reset,
    getCellNV, getCellKH, isLoading, isLoaded,
  }
}