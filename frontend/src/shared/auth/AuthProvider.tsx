import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import type { User, Session } from '@/types'

interface AuthContextValue extends Session {
  login: (username: string, password: string) => Promise<boolean>
  logout: () => Promise<void>
  loading: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState('')
  const [loading, setLoading] = useState(true)

  // Check session on mount (Flask session cookie)
  useEffect(() => {
    checkSession()
  }, [])

  async function checkSession() {
    try {
      // Try to access a protected endpoint to verify session
      const res = await fetch('/api/data-status', { credentials: 'same-origin' })
      if (res.ok) {
        // Session valid — user info comes from Flask template globals
        // For now, we parse it from a meta tag or a dedicated endpoint
        // TODO: Create a /api/me endpoint in Flask
        setLoading(false)
        return
      }
    } catch {
      // ignore
    }
    setUser(null)
    setToken('')
    setLoading(false)
  }

  async function login(username: string, password: string): Promise<boolean> {
    // Flask login is form-based, so we POST to /login
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    const res = await fetch('/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
      redirect: 'manual', // Don't follow redirect
      credentials: 'same-origin',
    })

    // Flask redirects to /dashboards on success, /login on failure
    if (res.type === 'opaqueredirect' || res.status === 302 || res.redirected) {
      await checkSession()
      return true
    }
    return false
  }

  async function logout() {
    await fetch('/logout', { credentials: 'same-origin' })
    setUser(null)
    setToken('')
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!user || !loading, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
