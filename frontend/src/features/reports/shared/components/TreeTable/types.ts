// ============================================================================
// TreeTable Types — Dùng chung cho mọi báo cáo dạng cây NV → KH
// ============================================================================

/** Nhân viên từ API hierarchy */
export interface NVRaw {
  ma_nvkd: string
  ten_nvkd: string
  ma_ql: string | null
  level: number
  stt_nhom: string
  ma_bp?: string
}

/** Node trong cây NV đã build, có children + dữ liệu aggregate */
export interface NVNode extends NVRaw {
  children: NVNode[]
  /** Dữ liệu theo từng cột: { colId: { kh: { maKH: value }, total: number } } */
  _vals: Record<string, ColumnData>
}

/** Dữ liệu 1 cột cho 1 NV node */
export interface ColumnData {
  /** Giá trị theo từng khách hàng */
  kh: Record<string, number>
  /** Tổng cộng (bao gồm con) — null nếu chưa tải */
  total: number | null
}

/** Khách hàng từ API */
export interface KHRaw {
  ma_kh: string
  ten_kh: string
  ma_nvkd: string
  ma_bp?: string
}

/** Định nghĩa 1 cột hiển thị trong bảng */
export interface ColumnDef {
  /** ID cột, khớp với key trong _vals */
  id: string
  /** Tiêu đề chính */
  label: string
  /** Dòng phụ (ngày tháng, ghi chú) */
  subLabel?: string
  /** Nhóm CSS class */
  className?: string
  /** Chiều rộng tối thiểu */
  minWidth?: number
  /** Có phải cột "nghịch đảo" (dư nợ — số âm là tốt) */
  isInverse?: boolean
}

/** Hàng đã flatten để render */
export interface FlatRow {
  type: 'nv' | 'kh'
  /** Chỉ có khi type='nv' */
  node?: NVNode
  /** Chỉ có khi type='kh' */
  maKH?: string
  tenKH?: string
  parentNV?: NVNode
  /** Độ sâu tree (0 = root) */
  depth: number
  /** Ancestor info cho tree lines */
  ancestors: { cont: boolean }[]
  /** Là node cuối cùng trong nhóm */
  isLast: boolean
  /** Đang mở rộng (chỉ NV) */
  expanded?: boolean
  /** Có con không (chỉ NV) */
  hasKids?: boolean

  ancestorIds?: string[]
}

/** Trạng thái loading của từng cột */
export interface ColumnLoadState {
  loading: boolean
  loaded: boolean
  data: Record<string, Record<string, number>>  // { maNVKD: { maKH: value } }
}

/** Kỳ báo cáo */
export interface KyBaoCao {
  id: number
  ten_kbc: string
  loai: string
  nam: number
  thang?: number
  quy?: number
  parent_id?: number | null
  ngay_bd_xuat_ban: string
  ngay_kt_xuat_ban: string
  ngay_bd_thu_tien: string
  ngay_kt_thu_tien: string
  ngay_bd_lan_ki?: string
  ngay_kt_lan_ki?: string
  ngay_du_no_dau_ki: string
  ngay_du_no_cuoi_ki: string
  sort_order?: number
}