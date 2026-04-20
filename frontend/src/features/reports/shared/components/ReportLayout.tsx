// ============================================================================
// ReportLayout — Layout chung cho mọi trang báo cáo
//
// Cấu trúc:
//   ┌─────────────────────────────────────┐
//   │ Toolbar (slot: truyền vào từ page)  │
//   ├─────────────────────────────────────┤
//   │ Content (children)                  │
//   │ - Bảng dữ liệu                     │
//   │ - Empty state                       │
//   │ - Loading state                     │
//   └─────────────────────────────────────┘
// ============================================================================

import type { ReactNode } from 'react'

interface ReportLayoutProps {
  /** Tên báo cáo (hiện trên toolbar mobile) */
  title?: string
  /** Nội dung toolbar */
  toolbar?: ReactNode
  /** Nội dung chính (bảng) */
  children: ReactNode
  /** Đang tải lần đầu */
  loading?: boolean
  /** Thông báo lỗi */
  error?: string
  /** Thông báo rỗng */
  emptyMessage?: string
}

export function ReportLayout({
  title,
  toolbar,
  children,
  loading,
  error,
  emptyMessage,
}: ReportLayoutProps) {
  return (
    <div className="rpt-layout">
      {/* Toolbar */}
      {toolbar && <div className="rpt-toolbar">{toolbar}</div>}

      {/* Content */}
      <div className="rpt-content">
        {loading ? (
          <div className="rpt-state">
            <div className="rpt-spinner" />
            <span>Đang tải dữ liệu…</span>
          </div>
        ) : error ? (
          <div className="rpt-state rpt-state-err">
            <span>⚠ {error}</span>
          </div>
        ) : emptyMessage ? (
          <div className="rpt-state">
            <span>{emptyMessage}</span>
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  )
}