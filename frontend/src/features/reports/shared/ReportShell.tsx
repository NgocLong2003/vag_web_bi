import type { ReactNode } from 'react'
import { ReportLayout } from '@shared/ui/layout/ReportLayout'
import { BottomSheet } from '@shared/ui/layout/BottomSheet'
import { useLayoutStore } from '@shared/stores/useLayoutStore'
import { useResponsive } from '@shared/hooks/useResponsive'

interface ReportShellProps {
  /** Desktop toolbar content */
  toolbar?: ReactNode
  /** Main content (table, chart, etc.) */
  children: ReactNode
  /** Footer content (totals) */
  footer?: ReactNode
  /** Mobile bottom sheet definitions */
  sheets?: Record<string, { title: string; content: ReactNode }>
}

/**
 * ReportShell — wraps ReportLayout with mobile bottom sheet support.
 * Each report page composes this with its own toolbar, content, and sheets.
 *
 * Usage:
 *   <ReportShell
 *     toolbar={<>...filters, buttons...</>}
 *     footer={<TotalRow />}
 *     sheets={{
 *       filter: { title: 'Bộ lọc', content: <FilterSheet /> },
 *       mode: { title: 'Chế độ xem', content: <ModeSheet /> },
 *       actions: { title: 'Thao tác', content: <ActionsSheet /> },
 *     }}
 *   >
 *     <TreeTable data={...} />
 *   </ReportShell>
 */
export function ReportShell({ toolbar, children, footer, sheets }: ReportShellProps) {
  const activeSheet = useLayoutStore((s) => s.activeSheet)
  const closeSheet = useLayoutStore((s) => s.closeSheet)
  const { isMobile } = useResponsive()

  const currentSheet = activeSheet && sheets?.[activeSheet]

  return (
    <>
      <ReportLayout toolbar={toolbar} footer={footer}>
        {children}
      </ReportLayout>

      {/* Mobile bottom sheets */}
      {isMobile && currentSheet && (
        <BottomSheet open={!!currentSheet} onClose={closeSheet} title={currentSheet.title}>
          {currentSheet.content}
        </BottomSheet>
      )}
    </>
  )
}
