import type { ReactNode } from 'react'
import { useResponsive } from '@shared/hooks/useResponsive'

interface ReportLayoutProps {
  /** Desktop toolbar content (filters, buttons) */
  toolbar?: ReactNode
  /** Main table/chart content */
  children: ReactNode
  /** Footer content (totals row) */
  footer?: ReactNode
}

/**
 * ReportLayout — standard wrapper for report pages.
 *
 * Desktop:
 *   ┌─ Toolbar (filters, export, etc.) ──┐
 *   ├────────────────────────────────────┤
 *   │ Content (scrollable table/chart)    │
 *   ├────────────────────────────────────┤
 *   └─ Footer (sticky totals) ───────────┘
 *
 * Mobile:
 *   ┌────────────────────────────────────┐
 *   │ Content (full height, scroll)       │
 *   │ (toolbar items → BottomDock sheets) │
 *   └────────────────────────────────────┘
 */
export function ReportLayout({ toolbar, children, footer }: ReportLayoutProps) {
  const { isMobile } = useResponsive()

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Toolbar — desktop only */}
      {!isMobile && toolbar && (
        <div className="flex h-[42px] shrink-0 items-center gap-2 border-b border-surface-2 bg-white px-3">
          {toolbar}
        </div>
      )}

      {/* Main scrollable content */}
      <div className="flex-1 overflow-auto overscroll-contain">
        {children}
      </div>

      {/* Footer — sticky bottom */}
      {footer && (
        <div className="shrink-0 border-t-2 border-surface-2 bg-white">
          {footer}
        </div>
      )}

      {/* Mobile spacer for bottom dock */}
      {isMobile && <div className="h-[52px] shrink-0" />}
    </div>
  )
}
