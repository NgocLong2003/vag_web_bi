// ============================================================================
// KBC (Kỳ Báo Cáo) Picker — Types
// ============================================================================

/** Raw KBC record from API /api/ky-bao-cao */
export interface KBCRecord {
  id: number
  ma_kbc: string
  ten_kbc: string
  loai_kbc: 'Năm' | 'Quý' | 'Tháng'
  parent_id: number | null
  sort_order: number
  ngay_du_no_dau_ki: string | null
  ngay_bd_xuat_ban: string | null
  ngay_kt_xuat_ban: string | null
  ngay_bd_thu_tien: string | null
  ngay_kt_thu_tien: string | null
  ngay_bd_lan_ki: string | null
  ngay_kt_lan_ki: string | null
  ngay_du_no_cuoi_ki: string | null
}

/** Merged KBC when multiple months are selected */
export interface MergedKBC {
  id: number
  ten_kbc: string
  loai_kbc: 'merged' | 'Tháng' | 'Quý' | 'Năm'
  ngay_du_no_dau_ki: string | null
  ngay_bd_xuat_ban: string | null
  ngay_kt_xuat_ban: string | null
  ngay_bd_thu_tien: string | null
  ngay_kt_thu_tien: string | null
  ngay_bd_lan_ki: string | null
  ngay_kt_lan_ki: string | null
  ngay_du_no_cuoi_ki: string | null
}

export interface KBCPickerProps {
  /** Raw list from API */
  kbcList: KBCRecord[]
  /** Current selection (controlled) */
  value: MergedKBC | null
  /** Called when selection changes — receives merged KBC or null */
  onChange: (kbc: MergedKBC | null) => void
  /** Trigger label override */
  label?: string
}