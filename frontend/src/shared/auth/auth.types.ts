// ============================================================================
// Auth Types — matches Flask /api/me response
// ============================================================================

export interface User {
  id: number
  username: string
  display_name: string
  role: 'admin' | 'user'
  khoi: string
  bo_phan: string
  chuc_vu: string
  ma_bp: string            // comma-separated: "VB,SF"
  ma_nvkd_list: string     // comma-separated: "TVV01,NVD01"
  email: string
  is_active: number
}

export interface DashboardPermission {
  id: number
  slug: string
  name: string
  type: string
}

export interface Permissions {
  allowed_bps: string[]
  ma_nvkd_list: string[]
  dashboards: DashboardPermission[]
}

export interface AuthState {
  user: User | null
  permissions: Permissions | null
  loading: boolean
  error: string | null
}