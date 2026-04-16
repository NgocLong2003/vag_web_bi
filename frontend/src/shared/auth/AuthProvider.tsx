import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import type { User, Session } from '@/types'

// ============================================================================
// AuthProvider — Checks Flask session via /api/me
//
// Flow:
//   Mount → GET /api/me → 200: set user → 401: redirect /login
//   Login: POST /login (form) via login() helper
//   Logout: GET /logout → redirect
// ============================================================================

interface AuthContextValue extends Session {
  login: (username: string, password: string) => Promise<boolean>
  logout: () => void
  refresh: () => Promise<void>
  loading: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

/** Map /api/me JSON to frontend User type */
function mapUser(raw: Record<string, unknown>, perms: Record<string, unknown>): User {
  const maBpRaw = (raw.ma_bp as string) || ''
  const nvkdRaw = (raw.ma_nvkd_list as string) || ''
  const dashboards = (perms.dashboards as Array<{ id: number }>) || []

  return {
    id: raw.id as number,
    username: raw.username as string,
    displayName: (raw.display_name as string) || (raw.username as string),
    role: raw.role as 'admin' | 'user',
    khoi: (raw.khoi as string) || '',
    boPhan: (raw.bo_phan as string) || '',
    chucVu: (raw.chuc_vu as string) || '',
    maNvkdList: nvkdRaw ? nvkdRaw.split(',').map(s => s.trim()).filter(Boolean) : [],
    maBp: maBpRaw ? maBpRaw.split(',').map(s => s.trim()).filter(Boolean) : [],
    email: (raw.email as string) || '',
    isActive: !!(raw.is_active),
    dashboardIds: dashboards.map(d => d.id),
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState('')
  const [loading, setLoading] = useState(true)

  const fetchMe = useCallback(async () => {
    try {
      const res = await fetch('/api/me', { credentials: 'same-origin' })

      if (res.status === 401 || res.status === 403) {
        setUser(null)
        setToken('')
        setLoading(false)
        return
      }

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }

      const data = await res.json()
      if (data.success && data.user) {
        setUser(mapUser(data.user, data.permissions || {}))
        setToken('session') // Flask session-based, no bearer token
      } else {
        setUser(null)
        setToken('')
      }
    } catch (e) {
      console.warn('Auth check failed:', (e as Error).message)
      setUser(null)
      setToken('')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMe()
  }, [fetchMe])

  async function login(username: string, password: string): Promise<boolean> {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    try {
      const res = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
        redirect: 'manual',
        credentials: 'same-origin',
      })

      // Flask redirects on success (302 → /dashboards)
      if (res.type === 'opaqueredirect' || res.status === 302 || res.redirected) {
        await fetchMe()
        return !!user
      }

      // Try to parse error from HTML (Flask renders login.html with error)
      return false
    } catch {
      return false
    }
  }

  function logout() {
    window.location.href = '/logout'
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        login,
        logout,
        refresh: fetchMe,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}