import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@shared/auth/AuthProvider'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    const ok = await login(username, password)
    if (ok) {
      navigate('/dashboards', { replace: true })
    } else {
      setError('Sai tên đăng nhập hoặc mật khẩu')
    }
    setLoading(false)
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-gradient-to-br from-[#0f2027] via-[#203a43] to-[#2c5364] p-5">
      <div className="w-full max-w-[380px] rounded-xl bg-white/95 p-10 shadow-2xl">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-extrabold text-surface-7">VietAnh BI Dashboard</h1>
          <p className="mt-1 text-sm text-surface-4">Đăng nhập để xem báo cáo</p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-center text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-semibold text-surface-5">Tên đăng nhập</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              autoComplete="username"
              className="w-full rounded-lg border-[1.5px] border-surface-2 px-3 py-2.5 text-sm outline-none transition focus:border-brand-600 focus:ring-2 focus:ring-brand-600/10"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-surface-5">Mật khẩu</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full rounded-lg border-[1.5px] border-surface-2 px-3 py-2.5 text-sm outline-none transition focus:border-brand-600 focus:ring-2 focus:ring-brand-600/10"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-brand-600 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
          </button>
        </form>

        <p className="mt-6 text-center text-[11px] text-surface-3">
          Ban Chiến Lược — Việt Anh Group
        </p>
      </div>
    </div>
  )
}
