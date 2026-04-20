// ============================================================================
// useHierarchy — Fetch danh sách NV phân cấp + build tree
// Dùng chung cho mọi báo cáo có cây NV → KH
// ============================================================================

import { useState, useCallback } from 'react'
import { apiClient } from '@shared/api/client'
import type { NVRaw, NVNode, KHRaw } from '../components/TreeTable/types'

interface HierarchyState {
  /** Map mã NVKD → node */
  nvMap: Map<string, NVNode>
  /** Danh sách flat gốc */
  hierarchy: NVNode[]
  /** Map mã KH → thông tin KH */
  khMap: Map<string, KHRaw>
  /** Map mã KH → tên KH (dùng để hiển thị, có thể bổ sung từ data) */
  khNames: Map<string, string>
  /** Đang tải */
  loading: boolean
  /** Lỗi */
  error: string
}

export function useHierarchy(apiBase: string) {
  const [state, setState] = useState<HierarchyState>({
    nvMap: new Map(),
    hierarchy: [],
    khMap: new Map(),
    khNames: new Map(),
    loading: false,
    error: '',
  })

  /** Fetch hierarchy + khách hàng từ API, build tree */
  const load = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: '' }))
    try {
      const [rH, rK] = await Promise.all([
        apiClient.get<{ success: boolean; data: NVRaw[]; error?: string }>(`${apiBase}/api/hierarchy`),
        apiClient.get<{ success: boolean; data: KHRaw[] }>(`${apiBase}/api/khachhang`),
      ])

      if (!rH.success) throw new Error(rH.error || 'Không tải được danh sách nhân viên')

      // Build NV map + tree
      const nvMap = new Map<string, NVNode>()
      rH.data.forEach(h => {
        nvMap.set(h.ma_nvkd, { ...h, children: [], _vals: {} })
      })
      // Link parent → children
      rH.data.forEach(h => {
        if (h.ma_ql && nvMap.has(h.ma_ql)) {
          nvMap.get(h.ma_ql)!.children.push(nvMap.get(h.ma_nvkd)!)
        }
      })
      // Sort children by stt_nhom
      nvMap.forEach(n => {
        n.children.sort((a, b) => a.stt_nhom.localeCompare(b.stt_nhom))
      })

      // Build KH maps
      const khMap = new Map<string, KHRaw>()
      const khNames = new Map<string, string>()
      if (rK.success) {
        rK.data.forEach(k => {
          if (k.ma_kh) {
            khMap.set(k.ma_kh, k)
            khNames.set(k.ma_kh, k.ten_kh)
          }
        })
      }

      setState({
        nvMap,
        hierarchy: Array.from(nvMap.values()),
        khMap,
        khNames,
        loading: false,
        error: '',
      })

      return { nvMap, hierarchy: rH.data, khMap, khNames }
    } catch (e: any) {
      setState(prev => ({ ...prev, loading: false, error: e.message || String(e) }))
      return null
    }
  }, [apiBase])

  /** Thêm tên KH từ data response (các API trả thêm ten_kh) */
  const addKHNames = useCallback((records: Array<{ ma_kh?: string; ten_kh?: string }>) => {
    setState(prev => {
      const names = new Map(prev.khNames)
      records.forEach(r => {
        if (r.ma_kh && r.ten_kh) names.set(r.ma_kh, r.ten_kh)
      })
      return { ...prev, khNames: names }
    })
  }, [])

  return { ...state, load, addKHNames }
}