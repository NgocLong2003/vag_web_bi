import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { BottomDock } from './BottomDock'
import { ToastContainer } from '@shared/ui/feedback/Toast'
import { useResponsive } from '@shared/hooks/useResponsive'

/**
 * AppShell — main layout wrapper for all authenticated pages.
 *
 * Desktop (split-pill header, no sidebar):
 *   ┌─────────────────────────────────────┐
 *   │ [Logo|DB name|badge]    [AI|Alert|…]│  ← floating pills (60px area)
 *   │                                     │
 *   │         <Outlet />                  │
 *   │         (full width)                │
 *   │                                     │
 *   └─────────────────────────────────────┘
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

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      {/* Header — split pills on desktop, hidden on mobile */}
      {!isMobile && <Header />}

      {/* Main content area — full width, no sidebar */}
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>

      {/* Mobile bottom dock */}
      {isMobile && <BottomDock />}

      {/* Toasts */}
      <ToastContainer />
    </div>
  )
}