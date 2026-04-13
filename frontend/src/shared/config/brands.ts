// ============================================================================
// BRANDS CONFIG — Danh sách bộ phận / thương hiệu
//
// Sửa link ảnh, thêm bớt BP → sửa file này.
// Sau này nếu muốn dynamic → chuyển sang API + admin panel.
// ============================================================================

export interface Brand {
  ma_bp: string
  thuong_hieu: string
  /** Logo dọc — dùng cho slicer dải ngang (Loại 2) */
  logo_vertical: string
  /** Logo ngang — dùng cho slicer dropdown (Loại 1). Để trống nếu chưa có. */
  logo_horizontal: string
  /** Thứ tự hiển thị */
  sort_order: number
}

export const BRANDS: Brand[] = [
    {
    ma_bp: '',
    thuong_hieu: 'Việt Anh Group',
    logo_vertical: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-vietanh-group-1.png',
    logo_horizontal: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-vietanh-group-2.png',
    sort_order: 0,
  },
    {
    ma_bp: 'VA',
    thuong_hieu: 'Viavet',
    logo_vertical: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-viavet.png',
    logo_horizontal: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-vietanh-group-2.png',
    sort_order: 1,
  },
  {
    ma_bp: 'DF',
    thuong_hieu: 'Dufavet',
    logo_vertical: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-dufafarm.png',
    logo_horizontal: 'https://dufafarm.com/wp-content/uploads/2023/11/logo_dufafam.png',
    sort_order: 2,
  },
  {
    ma_bp: 'XK',
    thuong_hieu: 'Xuất khẩu',
    logo_vertical: 'https://sanfovet.com/storage/logo/Logo-sanfovet.svg',
    logo_horizontal: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-vietanh-group-2.png',
    sort_order: 3,
  },
  {
    ma_bp: 'SF',
    thuong_hieu: 'Sanfovet',
    logo_vertical: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-sanfovet.png',
    logo_horizontal: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-vietanh-group-2.png',
    sort_order: 4,
  },
  {
    ma_bp: 'TN',
    thuong_hieu: 'TPBVSK',
    logo_vertical: 'https://i.ibb.co/zv6J5mB/logo-sanfo.png',
    logo_horizontal: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-vietanh-group-2.png',
    sort_order: 5,
  },
  {
    ma_bp: 'XP,XT',
    thuong_hieu: 'ViaProtic',
    logo_vertical: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-viaprotic.png',
    logo_horizontal: 'https://viaprotic.com/wp-content/uploads/2024/08/ViaProtic-nlogo-e1758078930618.png',
    sort_order: 6,
  },
  {
    ma_bp: 'VB',
    thuong_hieu: 'Thủy sản',
    logo_vertical: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-vaq.png',
    logo_horizontal: 'https://vaq.com.vn/wp-content/uploads/2024/07/logo-vaq.png',
    sort_order: 7,
  },
  {
    ma_bp: 'DA',
    thuong_hieu: 'Dự án',
    logo_vertical: 'https://i.ibb.co/RTJBV2L9/D-N.png',
    logo_horizontal: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-vietanh-group-2.png',
    sort_order: 8,
  },
  {
    ma_bp: 'NL',
    thuong_hieu: 'NL',
    logo_vertical: 'https://i.ibb.co/ZzVwXKdZ/NL.png',
    logo_horizontal: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-vietanh-group-2.png',
    sort_order: 9,
  },
  {
    ma_bp: 'PR',
    thuong_hieu: 'Premix',
    logo_vertical: 'https://i.ibb.co/6JDCddsb/PREMIX.png',
    logo_horizontal: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-vietanh-group-2.png',
    sort_order: 10,
  },
  {
    ma_bp: 'XX',
    thuong_hieu: '(Trống)',
    logo_vertical: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS3Zm-wn8_4dSBt-wZBc9KvKZ-tAsfACL__bw&s',
    logo_horizontal: 'https://vietanh-group.com/wp-content/uploads/2024/05/logo-vietanh-group-2.png',
    sort_order: 99,
  },
]

/** Lookup brand by ma_bp */
export const BRAND_MAP = new Map(BRANDS.map((b) => [b.ma_bp, b]))

/** Get brand logo (vertical) by ma_bp, with fallback */
export function getBrandLogo(maBp: string, type: 'vertical' | 'horizontal' = 'vertical'): string {
  const brand = BRAND_MAP.get(maBp)
  if (!brand) return ''
  return type === 'horizontal' ? brand.logo_horizontal : brand.logo_vertical
}