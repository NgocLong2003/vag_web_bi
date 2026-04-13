import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { BottomDock } from './BottomDock'
import { ToastContainer } from '@shared/ui/feedback/Toast'
import { useResponsive } from '@shared/hooks/useResponsive'
import { useLayoutStore } from '@shared/stores/useLayoutStore'

/**
 * AppShell — main layout wrapper for all authenticated pages.
 *
 * Desktop:
 *   ┌─────────────────────────────────┐
 *   │ Header (40px)                   │
 *   ├──────────┬──────────────────────┤
 *   │ Sidebar  │ <Outlet />           │
 *   │ (slide)  │                      │
 *   └──────────┴──────────────────────┘
 *
 * Mobile:
 *   ┌─────────────────────┐
 *   │ <Outlet />           │
 *   │ (full height)        │
 *   ├─────────────────────┤
 *   │ BottomDock (52px)    │
 *   └─────────────────────┘
 */
export function AppShell() {
  const { isMobile } = useResponsive()
  const sidebarOpen = useLayoutStore((s) => s.sidebarOpen)
  const setSidebarOpen = useLayoutStore((s) => s.setSidebarOpen)

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      {/* Header — always visible on desktop, hidden on mobile (replaced by BottomDock) */}
      {!isMobile && <Header />}

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — slide-in overlay on both desktop and mobile */}
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        {/* Main content area */}
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>

      {/* Mobile bottom dock */}
      {isMobile && <BottomDock />}

      {/* Toasts */}
      <ToastContainer />
    </div>
  )
}
