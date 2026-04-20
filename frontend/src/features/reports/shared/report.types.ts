import type { NVNode, KhachHang, KyBaoCao, MergedKBC } from '@/types'

/** Column config for tree-based reports (Kinh Doanh, Khách Hàng) */
export interface ReportColumnDef {
  id: string
  type: 'cn' | 'ds' | 'dt' | 'custom'
  label: string
  accent: string               // CSS class for header color
  apiEndpoint: string
  dateFields: {
    dateA: string
    dateB?: string
  }
}

/** Data per column: nvkd → kh → value */
export type ColumnData = Record<string, Record<string, number>>

/** Aggregated values for a tree node */
export interface AggregatedValues {
  /** Per-KH values */
  kh: Record<string, number>
  /** Roll-up total (sum of own KH + children totals) */
  total: number | null
}

/** Extended NV node with aggregated values per column */
export interface ReportNVNode extends NVNode {
  _vals: Record<string, AggregatedValues>
}

/** Row in rendered output (for Excel export) */
export interface ExportRow {
  type: 'nv' | 'kh' | 'total'
  depth: number
  name: string
  values: (number | null)[]
}

/** Current KBC — single or merged */
export type CurrentKBC = KyBaoCao | MergedKBC | null

/** Report init data (loaded once) */
export interface ReportInitData {
  hierarchy: NVNode[]
  nvMap: Map<string, NVNode>
  roots: NVNode[]
  khMap: Map<string, KhachHang>
  khNames: Map<string, string>
  allowedNV: Set<string>
  allowedBP: string[]
}
