import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { BottomDock } from './BottomDock'
import { ToastContainer } from '@shared/ui/feedback/Toast'
import { useResponsive } from '@shared/hooks/useResponsive'

export function AppShell() {
  const { isMobile } = useResponsive()

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      {!isMobile && <Header />}

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>

      {isMobile && <BottomDock />}
      <ToastContainer />
    </div>
  )
}