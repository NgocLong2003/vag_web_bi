import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '@shared/auth/AuthProvider'
import {
  BarChart3,
  FileSpreadsheet,
  Activity,
  Shield,
  Settings,
  LogOut,
  X,
  Home,
} from 'lucide-react'
import { useEffect, useRef } from 'react'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { user, logout } = useAuth()
  const location = useLocation()
  const menuRef = useRef<HTMLDivElement>(null)

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  // Swipe right to close (mobile)
  useEffect(() => {
    if (!open || !menuRef.current) return
    let startX = 0
    let currentX = 0
    let dragging = false
    const el = menuRef.current

    function onStart(e: TouchEvent) {
      startX = e.touches[0].clientX
      currentX = startX
      dragging = true
      el.style.transition = 'none'
    }
    function onMove(e: TouchEvent) {
      if (!dragging) return
      currentX = e.touches[0].clientX
      const dx = Math.min(0, currentX - startX) // Only allow left-swipe (close)
      el.style.transform = `translateX(${dx}px)`
    }
    function onEnd() {
      if (!dragging) return
      dragging = false
      el.style.transition = ''
      if (startX - currentX > 60) {
        onClose()
      } else {
        el.style.transform = ''
      }
    }

    el.addEventListener('touchstart', onStart, { passive: true })
    document.addEventListener('touchmove', onMove, { passive: true })
    document.addEventListener('touchend', onEnd)
    return () => {
      el.removeEventListener('touchstart', onStart)
      document.removeEventListener('touchmove', onMove)
      document.removeEventListener('touchend', onEnd)
    }
  }, [open, onClose])

  // TODO: Load dashboards from API or pass as props
  const dashboards = [
    { slug: 'bao-cao-kinh-doanh', name: 'Báo cáo Kinh Doanh', icon: BarChart3 },
    { slug: 'bao-cao-khach-hang', name: 'Báo cáo Khách Hàng', icon: FileSpreadsheet },
    { slug: 'bao-cao-chi-tiet', name: 'Báo cáo Chi Tiết', icon: FileSpreadsheet },
    { slug: 'bao-cao-ban-ra', name: 'Báo cáo Bán Ra', icon: FileSpreadsheet },
    { slug: 'bao-cao-kpi', name: 'Báo cáo KPI', icon: Activity },
  ]

  return (
    <>
      {/* Overlay */}
      <div
        className={`fixed inset-0 z-[9998] bg-black/40 backdrop-blur-sm transition-opacity ${
          open ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
      />

      {/* Sidebar panel */}
      <nav
        ref={menuRef}
        className={`fixed bottom-0 left-0 top-0 z-[9999] flex w-[260px] max-w-[80vw] flex-col overflow-y-auto bg-surface-7 text-white shadow-xl transition-transform duration-300 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Head */}
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
          <span className="text-sm font-bold">{user?.displayName || user?.username}</span>
          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-md bg-white/10 text-white/60 hover:bg-white/15"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Dashboard list */}
        <div className="flex-1 py-2">
          <Link
            to="/dashboards"
            onClick={onClose}
            className="flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-white/70 hover:bg-white/5 hover:text-white"
          >
            <Home className="h-4 w-4" />
            Tất cả Dashboard
          </Link>

          <div className="px-4 pb-1 pt-3 text-[10px] font-bold uppercase tracking-wider text-white/30">
            Báo cáo
          </div>
          {dashboards.map((d) => {
            const isActive = location.pathname.includes(d.slug)
            return (
              <Link
                key={d.slug}
                to={`/r/${d.slug}`}
                onClick={onClose}
                className={`flex items-center gap-3 px-4 py-2.5 text-[13px] font-medium transition-colors ${
                  isActive
                    ? 'bg-white/10 font-bold text-white'
                    : 'text-white/70 hover:bg-white/5 hover:text-white'
                }`}
              >
                <d.icon className="h-4 w-4 shrink-0" />
                {d.name}
              </Link>
            )
          })}
        </div>

        {/* Footer actions */}
        <div className="border-t border-white/10 py-2">
          {user?.role === 'admin' && (
            <Link
              to="/admin"
              onClick={onClose}
              className="flex items-center gap-3 px-4 py-2.5 text-[13px] text-white/70 hover:bg-white/5 hover:text-white"
            >
              <Shield className="h-4 w-4" />
              Quản trị
            </Link>
          )}
          <Link
            to="/settings"
            onClick={onClose}
            className="flex items-center gap-3 px-4 py-2.5 text-[13px] text-white/70 hover:bg-white/5 hover:text-white"
          >
            <Settings className="h-4 w-4" />
            Cài đặt
          </Link>
          <button
            onClick={() => {
              onClose()
              logout()
            }}
            className="flex w-full items-center gap-3 px-4 py-2.5 text-[13px] text-red-300 hover:bg-white/5"
          >
            <LogOut className="h-4 w-4" />
            Đăng xuất
          </button>
        </div>
      </nav>
    </>
  )
}
