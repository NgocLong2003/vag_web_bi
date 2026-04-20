// ============================================================================
// useKhachHangData — State + fetch logic cho Báo cáo Khách hàng
//
// Quản lý:
//   - Load 7 cột data song song (Promise.all)
//   - Parse response theo từng loại API (congno, doanhso, doanhthu, ...)
//   - Filter tt2 theo BP nhóm A
//   - Aggregate lên cây NV
// ============================================================================

import { useCallback } from 'react'
import { useColumnLoader } from '../../shared/hooks/useColumnLoader'
import type { NVNode, KyBaoCao } from '../../shared/components/TreeTable/types'
import { COLUMN_IDS, computeDates, BP_NHOM_A } from './columns'

const API_BASE = '/reports/bao-cao-khach-hang'

/** Parse response công nợ → { maNVKD: { maKH: value } } */
function parseCN(data: any[]): Record<string, Record<string, number>> {
  const m: Record<string, Record<string, number>> = {}
  data.forEach(r => {
    const nv = r.ma_nvkd || '_UNK'
    if (!m[nv]) m[nv] = {}
    m[nv][r.ma_kh] = (m[nv][r.ma_kh] || 0) + (r.du_no_ck || 0)
  })
  return m
}

/** Parse response doanh số */
function parseDS(data: any[]): Record<string, Record<string, number>> {
  const m: Record<string, Record<string, number>> = {}
  data.forEach(r => {
    const nv = r.ma_nvkd || '_UNK'
    if (!m[nv]) m[nv] = {}
    m[nv][r.ma_kh] = (m[nv][r.ma_kh] || 0) + (r.tong_doanhso || 0)
  })
  return m
}

/** Parse response doanh thu (thanh toán) */
function parseDT(data: any[]): Record<string, Record<string, number>> {
  const m: Record<string, Record<string, number>> = {}
  data.forEach(r => {
    const nv = r.ma_nvkd || '_UNK'
    if (!m[nv]) m[nv] = {}
    m[nv][r.ma_kh] = (m[nv][r.ma_kh] || 0) + (r.doanhthu || 0)
  })
  return m
}

/** Parse response dư nợ trong kỳ */
function parseDNTK(data: any[]): Record<string, Record<string, number>> {
  const m: Record<string, Record<string, number>> = {}
  data.forEach(r => {
    const nv = r.ma_nvkd || '_UNK'
    if (!m[nv]) m[nv] = {}
    m[nv][r.ma_kh] = (m[nv][r.ma_kh] || 0) + (r.du_no_trong_ky || 0)
  })
  return m
}

/** Parse response dư nợ cuối kỳ */
function parseDNCK(data: any[]): Record<string, Record<string, number>> {
  const m: Record<string, Record<string, number>> = {}
  data.forEach(r => {
    const nv = r.ma_nvkd || '_UNK'
    if (!m[nv]) m[nv] = {}
    m[nv][r.ma_kh] = (m[nv][r.ma_kh] || 0) + (r.du_no_cuoi_ky || 0)
  })
  return m
}

/** Gọi API POST */
async function fetchPost(url: string, body: Record<string, any>): Promise<any> {
  const res = await fetch(API_BASE + url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return res.json()
}

/** Filter tt2: chỉ giữ KH thuộc nhóm A */
function filterTT2ByBP(
  data: Record<string, Record<string, number>>,
  khMap: Map<string, { ma_bp?: string }>,
): Record<string, Record<string, number>> {
  const filtered: Record<string, Record<string, number>> = {}
  Object.entries(data).forEach(([nv, khData]) => {
    filtered[nv] = {}
    Object.entries(khData).forEach(([maKH, val]) => {
      const kh = khMap.get(maKH)
      const bpKH = kh?.ma_bp || ''
      if (!bpKH || BP_NHOM_A.includes(bpKH)) {
        filtered[nv][maKH] = val
      }
    })
  })
  return filtered
}

export function useKhachHangData() {
  const loader = useColumnLoader()

  /** Load tất cả 7 cột cho 1 kỳ báo cáo */
  const loadAllData = useCallback(async (
    kbc: KyBaoCao,
    selectedBP: string,
    allowedNV: Set<string>,
    userNvkdList: string[],
    userBpList: string[],
    khMap: Map<string, { ma_bp?: string }>,
    selectedKH: string | null,
  ) => {
    const dates = computeDates(kbc)
    const { dDNDK, dBDXB, dKTXB, dBDTT, dKTTT, dBDLK, dKTLK, dDNCK, ngayTruocLK } = dates

    if (!dDNDK || !dBDXB || !dKTXB || !dBDTT || !dKTTT || !dDNCK) {
      throw new Error('Kỳ báo cáo thiếu ngày, không thể tải dữ liệu')
    }

    const bp = selectedBP || (userBpList.length ? userBpList.join(',') : '')
    const nv = allowedNV.size > 0 && userNvkdList.length ? [...allowedNV].join(',') : ''
    const kh = selectedKH || ''

    // Tạo fetchers cho từng cột
    const fetchers: Record<string, () => Promise<Record<string, Record<string, number>>>> = {
      du_no_dk: async () => {
        const r = await fetchPost('/api/congno', { ngay_cut: dDNDK, ma_bp: bp, ds_nvkd: nv, ds_kh: kh })
        return r.success ? parseCN(r.data) : {}
      },
      ban_ra: async () => {
        const r = await fetchPost('/api/doanhso', { ngay_a: dBDXB, ngay_b: dKTXB, ma_bp: bp, ds_nvkd: nv, ds_kh: kh })
        return r.success ? parseDS(r.data) : {}
      },
      tt1: async () => {
        if (!dBDTT || !ngayTruocLK) return {}
        const r = await fetchPost('/api/doanhthu', { ngay_a: dBDTT, ngay_b: ngayTruocLK, ngay_a2: dBDXB, ngay_b2: dKTXB, ma_bp: bp, ds_nvkd: nv, ds_kh: kh })
        return r.success ? parseDT(r.data) : {}
      },
      tt2: async () => {
        if (!dBDLK || !dKTTT) return {}
        const r = await fetchPost('/api/doanhthu', { ngay_a: dBDLK, ngay_b: dKTTT, ma_bp: bp, ds_nvkd: nv, ds_kh: kh })
        const parsed = r.success ? parseDT(r.data) : {}
        // Filter: chỉ giữ KH nhóm A
        return filterTT2ByBP(parsed, khMap)
      },
      du_no_tk: async () => {
        const r = await fetchPost('/api/dunotrongky', { ngay_a_hang: dBDXB, ngay_b_hang: dKTXB, ngay_a_tien: dBDTT, ngay_b_tien: dKTTT, ma_bp: bp, ds_nvkd: nv, ds_kh: kh })
        return r.success ? parseDNTK(r.data) : {}
      },
      du_no_ct: async () => {
        const r = await fetchPost('/api/congno', { ngay_cut: dDNCK, ma_bp: bp, ds_nvkd: nv, ds_kh: kh })
        return r.success ? parseCN(r.data) : {}
      },
      du_no_ck: async () => {
        const r = await fetchPost('/api/dunocuoiky', { ngay_cut: dKTTT, ngay_a_lk: dBDLK, ngay_b_lk: dKTLK, ma_bp: bp, ds_nvkd: nv, ds_kh: kh })
        return r.success ? parseDNCK(r.data) : {}
      },
    }

    await loader.loadAll(fetchers)
  }, [loader])

  /** Lấy giá trị ô — hỗ trợ tt_merged (gộp tt1 + tt2) */
  const getCellNV = useCallback((node: NVNode, colId: string): number | null => {
    if (colId === 'tt_merged') {
      const v1 = node._vals.tt1?.total ?? null
      const v2 = node._vals.tt2?.total ?? null
      if (v1 == null && v2 == null) return null
      return (v1 || 0) + (v2 || 0)
    }
    return loader.getCellNV(node, colId)
  }, [loader])

  const getCellKH = useCallback((parentNV: NVNode, maKH: string, colId: string): number | null => {
    if (colId === 'tt_merged') {
      const v1 = parentNV._vals.tt1?.kh[maKH] ?? null
      const v2 = parentNV._vals.tt2?.kh[maKH] ?? null
      if (v1 == null && v2 == null) return null
      return (v1 || 0) + (v2 || 0)
    }
    return loader.getCellKH(parentNV, maKH, colId)
  }, [loader])

  const isLoading = useCallback((colId: string): boolean => {
    if (colId === 'tt_merged') return loader.isLoading('tt1') || loader.isLoading('tt2')
    return loader.isLoading(colId)
  }, [loader])

  const isLoaded = useCallback((colId: string): boolean => {
    if (colId === 'tt_merged') return loader.isLoaded('tt1') || loader.isLoaded('tt2')
    return loader.isLoaded(colId)
  }, [loader])

  return {
    columns: loader.columns,
    loadAllData,
    aggregate: loader.aggregate,
    reset: loader.reset,
    getCellNV,
    getCellKH,
    isLoading,
    isLoaded,
  }
}