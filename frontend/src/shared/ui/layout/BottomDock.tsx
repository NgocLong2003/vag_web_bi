import { useLayoutStore } from '@shared/stores/useLayoutStore'
import { useNavigate } from 'react-router-dom'
import {
  Home,
  Search,
  BarChart3,
  SlidersHorizontal,
  MoreVertical,
} from 'lucide-react'

// ============================================================================
// STANDARDS: Bố cục Mobile
// - Mobile thì bỏ Header, thay bằng Bottom Dock
// - Home ngoài cùng tay trái
// - Còn lại tùy sắp xếp theo từng trang
// ============================================================================

interface DockAction {
  id: string
  icon: typeof Home
  label: string
  accent?: boolean
  onClick: () => void
}

interface BottomDockProps {
  /** Override default actions — each report page can customize.
   *  Home luôn được thêm ngoài cùng bên trái, không cần khai báo lại. */
  actions?: DockAction[]
}

export function BottomDock({ actions }: BottomDockProps) {
  const navigate = useNavigate()
  const toggleSidebar = useLayoutStore((s) => s.toggleSidebar)
  const openSheet = useLayoutStore((s) => s.openSheet)

  // Home luôn ở vị trí đầu tiên (ngoài cùng tay trái)
  const homeAction: DockAction = {
    id: 'home',
    icon: Home,
    label: 'Home',
    onClick: () => navigate('/dashboards'),
  }

  // Default actions (sau Home), có thể bị override bởi prop `actions`
  const defaultActions: DockAction[] = [
    { id: 'nv', icon: Search, label: 'NV', onClick: () => openSheet('picker') },
    { id: 'view', icon: BarChart3, label: 'Xem', accent: true, onClick: () => openSheet('mode') },
    { id: 'filter', icon: SlidersHorizontal, label: 'Lọc', onClick: () => openSheet('filter') },
    { id: 'more', icon: MoreVertical, label: 'Khác', onClick: () => openSheet('actions') },
  ]

  // Home + (custom actions hoặc default actions)
  const items = [homeAction, ...(actions || defaultActions)]

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-[60] flex items-center justify-around border-t border-surface-2 bg-white px-2 pb-[env(safe-area-inset-bottom)] shadow-[0_-2px_12px_rgba(0,0,0,0.08)]"
      style={{ paddingTop: 6, paddingBottom: `calc(6px + env(safe-area-inset-bottom))` }}
    >
      {items.map((item) => (
        <button
          key={item.id}
          onClick={item.onClick}
          className={`flex min-w-[48px] flex-col items-center gap-0.5 rounded-lg px-2 py-1 transition-all active:scale-95 active:bg-surface-1 ${
            item.accent ? 'text-brand-600' : 'text-surface-5'
          }`}
        >
          <item.icon className="h-[18px] w-[18px]" />
          <span className="text-[9px] font-semibold">{item.label}</span>
        </button>
      ))}
    </nav>
  )
}
