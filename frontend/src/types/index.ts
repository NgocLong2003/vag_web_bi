// ═══════════════════════════════════════
// AUTH & USER
// ═══════════════════════════════════════

export interface User {
  id: number
  username: string
  displayName: string
  role: 'admin' | 'user'
  khoi: string
  boPhan: string
  chucVu: string
  maNvkdList: string[]       // RLS: NV codes this user can see
  maBp: string[]             // Admin scope: BPs this admin manages
  email: string
  isActive: boolean
  dashboardIds: number[]     // Dashboards this user can access
}

export interface Session {
  user: User | null
  token: string
  isAuthenticated: boolean
}

// ═══════════════════════════════════════
// HIERARCHY & DIMENSIONS
// ═══════════════════════════════════════

export interface HierarchyNode {
  ma_nvkd: string
  ten_nvkd: string
  ma_ql: string
  stt_nhom: string
  level: number
}

export interface NVNode extends HierarchyNode {
  children: NVNode[]
}

export interface KhachHang {
  ma_kh: string
  ten_kh: string
  ma_bp: string
  ma_nvkd: string
}

// ═══════════════════════════════════════
// KỲ BÁO CÁO
// ═══════════════════════════════════════

export interface KyBaoCao {
  id: number
  ma_kbc: string
  ten_kbc: string
  loai_kbc: 'Tháng' | 'Quý' | 'Năm'
  parent_id: number | null
  sort_order: number
  ngay_bd_xuat_ban: string | null
  ngay_kt_xuat_ban: string | null
  ngay_bd_thu_tien: string | null
  ngay_kt_thu_tien: string | null
  ngay_bd_lan_ki: string | null
  ngay_kt_lan_ki: string | null
  ngay_du_no_dau_ki: string | null
  ngay_du_no_cuoi_ki: string | null
}

export interface MergedKBC {
  id: number
  ten_kbc: string
  loai_kbc: 'merged'
  ngay_bd_xuat_ban: string | null
  ngay_kt_xuat_ban: string | null
  ngay_bd_thu_tien: string | null
  ngay_kt_thu_tien: string | null
  ngay_bd_lan_ki: string | null
  ngay_kt_lan_ki: string | null
  ngay_du_no_dau_ki: string | null
  ngay_du_no_cuoi_ki: string | null
}

// ═══════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════

export interface Dashboard {
  id: number
  slug: string
  name: string
  powerbiUrl: string
  description: string
  dashboardType: 'powerbi' | 'analytics' | 'report'
  category: string
  isActive: boolean
  sortOrder: number
  /** SVG path data for card icon (admin configurable) */
  iconSvg: string
  /** Color theme for card: teal, blue, purple, amber, rose, emerald, indigo, cyan */
  color: string
}

// ═══════════════════════════════════════
// REPORT DATA SHAPES
// ═══════════════════════════════════════

export interface ReportColumn {
  id: string
  type: 'cn' | 'ds' | 'dt'   // Công nợ, Doanh số, Doanh thu
  label: string
  dateA: string
  dateB: string
  data: Record<string, Record<string, number>>  // nvkd → kh → value
  loaded: boolean
  loading: boolean
}

// Tree row types for rendering
export type TreeRowType = 'nv' | 'kh' | 'ds' | 'dt' | 'total'

export interface TreeRow {
  type: TreeRowType
  depth: number
  name: string
  code?: string
  values: (number | null)[]
  node?: NVNode
  maKh?: string
  expanded?: boolean
  hasKids?: boolean
  isLast?: boolean
  ancestors?: { cont: boolean }[]
}

// ═══════════════════════════════════════
// API RESPONSES
// ═══════════════════════════════════════

export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: string
  count?: number
}

export interface ApiOkResponse<T> {
  ok: boolean
  data?: T
  error?: string
  message?: string
}