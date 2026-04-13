import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '@shared/auth/AuthProvider'
import { useLayoutStore } from '@shared/stores/useLayoutStore'
import { Menu, Settings, LogOut, Shield, ChevronDown } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

export function Header() {
  const { user, logout } = useAuth()
  const toggleSidebar = useLayoutStore((s) => s.toggleSidebar)
  const location = useLocation()
  const [fullscreen, setFullscreen] = useState(false)

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen()
      setFullscreen(true)
    } else {
      document.exitFullscreen()
      setFullscreen(false)
    }
  }

  useEffect(() => {
    const handler = () => setFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', handler)
    return () => document.removeEventListener('fullscreenchange', handler)
  }, [])

  return (
    <header className="flex h-10 shrink-0 items-center justify-between bg-surface-7 px-3 text-white">
      {/* Left: hamburger + brand */}
      <div className="flex items-center gap-2">
        <button
          onClick={toggleSidebar}
          className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-white/10"
          aria-label="Menu"
        >
          <Menu className="h-4 w-4" />
        </button>

        <Link to="/dashboards" className="text-sm font-bold tracking-tight hover:text-white/80">
          VietAnh BI
        </Link>
      </div>

      {/* Center: fullscreen toggle */}
      <button
        onClick={toggleFullscreen}
        className="rounded-md border border-white/15 bg-white/5 px-3 py-1 text-[10px] font-semibold tracking-wide text-white/60 hover:bg-white/15 hover:text-white"
      >
        {fullscreen ? 'THOÁT TOÀN MÀN HÌNH' : 'TOÀN MÀN HÌNH'}
      </button>

      {/* Right: user info + actions */}
      <div className="flex items-center gap-2 text-xs">
        <span className="text-white/70">{user?.displayName || user?.username}</span>

        {user?.role === 'admin' && (
          <Link
            to="/admin"
            className="flex items-center gap-1 rounded-md border border-white/15 bg-white/10 px-2.5 py-1 text-[11px] font-semibold hover:bg-white/20"
          >
            <Shield className="h-3 w-3" />
            Quản trị
          </Link>
        )}

        <Link
          to="/settings"
          className="flex items-center gap-1 rounded-md border border-white/15 bg-white/10 px-2.5 py-1 text-[11px] font-semibold hover:bg-white/20"
        >
          <Settings className="h-3 w-3" />
          Cài đặt
        </Link>

        <button
          onClick={logout}
          className="flex items-center gap-1 rounded-md border border-white/15 bg-white/10 px-2.5 py-1 text-[11px] font-semibold hover:bg-white/20"
        >
          <LogOut className="h-3 w-3" />
          Thoát
        </button>
      </div>
    </header>
  )
}
