// ============================================================================
// BRANDS CONFIG — Danh sach bo phan / thuong hieu
//
// Logo luu tai: public/assets/logos/vertical/ va /horizontal/
// Khi chua co file local, dung URL ben ngoai lam fallback.
// Sau khi download het logo ve local, xoa URL fallback di.
// ============================================================================

export interface Brand {
  ma_bp: string
  thuong_hieu: string
  logo_vertical: string
  logo_horizontal: string
  sort_order: number
}

/** Base path for logo assets (served by Vite from public/) */
const V = '/assets/logos/vertical/'
const H = '/assets/logos/horizontal/'

export const BRANDS: Brand[] = [
  {
    ma_bp: '',
    thuong_hieu: 'Viet Anh Group',
    logo_vertical: V + 'vietanh.png',
    logo_horizontal: H + 'vietanh.png',
    sort_order: 0,
  },
  {
    ma_bp: 'VA',
    thuong_hieu: 'Viavet',
    logo_vertical: V + 'va.png',
    logo_horizontal: H + 'va.png',
    sort_order: 1,
  },
  {
    ma_bp: 'DF',
    thuong_hieu: 'Dufavet',
    logo_vertical: V + 'df.png',
    logo_horizontal: H + 'df.png',
    sort_order: 2,
  },
  {
    ma_bp: 'XK',
    thuong_hieu: 'Xuat khau',
    logo_vertical: V + 'xk.png',
    logo_horizontal: H + 'xk.png',
    sort_order: 3,
  },
  {
    ma_bp: 'SF',
    thuong_hieu: 'Sanfovet',
    logo_vertical: V + 'sf.png',
    logo_horizontal: H + 'sf.png',
    sort_order: 4,
  },
  {
    ma_bp: 'TN',
    thuong_hieu: 'TPBVSK',
    logo_vertical: V + 'tn.png',
    logo_horizontal: H + 'tn.png',
    sort_order: 5,
  },
  {
    ma_bp: 'XP,XT',
    thuong_hieu: 'ViaProtic',
    logo_vertical: V + 'xp.png',
    logo_horizontal: H + 'xp.png',
    sort_order: 6,
  },
  {
    ma_bp: 'VB',
    thuong_hieu: 'Thuy san',
    logo_vertical: V + 'vb.png',
    logo_horizontal: H + 'vb.png',
    sort_order: 7,
  },
  {
    ma_bp: 'DA',
    thuong_hieu: 'Du an',
    logo_vertical: V + 'da.png',
    logo_horizontal: H + 'da.png',
    sort_order: 8,
  },
  {
    ma_bp: 'NL',
    thuong_hieu: 'NL',
    logo_vertical: V + 'nl.png',
    logo_horizontal: H + 'nl.png',
    sort_order: 9,
  },
  {
    ma_bp: 'PR',
    thuong_hieu: 'Premix',
    logo_vertical: V + 'pr.png',
    logo_horizontal: H + 'pr.png',
    sort_order: 10,
  },
  {
    ma_bp: 'XX',
    thuong_hieu: '(Trong)',
    logo_vertical: V + 'xx.png',
    logo_horizontal: H + 'xx.png',
    sort_order: 99,
  },
]

/** Lookup brand by ma_bp */
export const BRAND_MAP = new Map(BRANDS.map((b) => [b.ma_bp, b]))

/** Get brand logo by ma_bp */
export function getBrandLogo(maBp: string, type: 'vertical' | 'horizontal' = 'vertical'): string {
  const brand = BRAND_MAP.get(maBp)
  if (!brand) return ''
  return type === 'horizontal' ? brand.logo_horizontal : brand.logo_vertical
}