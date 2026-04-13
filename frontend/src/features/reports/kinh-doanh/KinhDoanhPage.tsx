import { useState, useCallback } from 'react'
import { ENDPOINTS } from '@shared/api/endpoints'
import { useFilterStore } from '@shared/stores/useFilterStore'
import { useResponsive } from '@shared/hooks/useResponsive'
import { ReportShell } from '@features/reports/_shared/ReportShell'
import { useReportData } from '@features/reports/_shared/useReportData'
import { LoadingOverlay } from '@shared/ui/feedback/LoadingOverlay'
import { EmptyState } from '@shared/ui/data-display/EmptyState'
import { ExportButton } from '@shared/ui/actions/ExportButton'
import { toast } from '@shared/ui/feedback/Toast'
import { today, firstDayOfMonth } from '@shared/utils/format'

/**
 * Báo cáo Kinh Doanh — reference implementation.
 *
 * Features to migrate from baocao_kinhdoanh/baocao_kd.html:
 * - Dynamic columns (add/remove/reorder: Công nợ, Doanh số, Doanh thu)
 * - Tree table (NV hierarchy → KH breakdown)
 * - Per-column date range + load
 * - Column drag-and-drop reorder
 * - NV picker (tree with checkbox, multi-select)
 * - BP selector
 * - Export Excel
 * - Mobile bottom dock + sheets
 * - Column resize
 * - Expand/collapse all
 */
export default function KinhDoanhPage() {
  const { data: reportData, isLoading, error } = useReportData({
    hierarchyUrl: ENDPOINTS.reports.kinhDoanh.hierarchy,
    khachhangUrl: ENDPOINTS.reports.kinhDoanh.khachhang,
  })

  const { isMobile } = useResponsive()
  const { selectedBP, setSelectedBP } = useFilterStore()
  const [allExpanded, setAllExpanded] = useState(true)

  // Column state
  const [columns, setColumns] = useState([
    { id: 'c0', type: 'cn' as const, label: 'Công nợ', dateA: today(), dateB: '', loaded: false, loading: false, data: {} },
    { id: 'c1', type: 'ds' as const, label: 'Doanh số', dateA: firstDayOfMonth(), dateB: today(), loaded: false, loading: false, data: {} },
    { id: 'c2', type: 'dt' as const, label: 'Doanh thu', dateA: firstDayOfMonth(), dateB: today(), loaded: false, loading: false, data: {} },
  ])

  if (isLoading) return <LoadingOverlay visible message="Đang tải cấu trúc..." />
  if (error) return <EmptyState message={`Lỗi: ${error}`} />
  if (!reportData) return <EmptyState message="Đang tải..." />

  // ─── Desktop Toolbar ───
  const toolbar = (
    <>
      {/* BP Selector */}
      <label className="text-[11px] font-semibold text-surface-4">BP:</label>
      <select
        value={selectedBP}
        onChange={(e) => setSelectedBP(e.target.value)}
        className="h-8 rounded-md border border-surface-2 bg-surface-0 px-2 text-xs font-semibold outline-none focus:border-brand-500"
      >
        {reportData.allowedBP.length > 1 && <option value="">Tất cả</option>}
        {reportData.allowedBP.map((bp) => (
          <option key={bp} value={bp}>{bp}</option>
        ))}
      </select>

      <div className="mx-1 h-5 w-px bg-surface-2" />

      {/* NV Picker trigger — TODO: integrate TreePicker component */}
      <button className="flex h-8 items-center gap-1.5 rounded-md border border-surface-2 bg-surface-0 px-3 text-xs font-semibold text-surface-5 hover:bg-white">
        NV <span className="rounded-full bg-surface-3 px-1.5 text-[10px] font-bold text-white">∞</span>
      </button>

      <div className="mx-1 h-5 w-px bg-surface-2" />

      {/* Expand/collapse */}
      <button
        onClick={() => setAllExpanded((v) => !v)}
        className="flex h-8 items-center gap-1 rounded-md border border-surface-2 bg-white px-3 text-xs font-semibold text-surface-5 hover:bg-surface-0"
      >
        {allExpanded ? 'Thu' : 'Mở'}
      </button>

      {/* Reload */}
      <button
        onClick={() => toast('TODO: Reload all columns')}
        className="flex h-8 items-center gap-1 rounded-md border border-surface-2 bg-white px-3 text-xs font-semibold text-surface-5 hover:bg-surface-0"
      >
        Tải lại
      </button>

      <div className="mx-1 h-5 w-px bg-surface-2" />

      {/* Add column */}
      <button className="flex h-8 items-center gap-1 rounded-md border border-brand-500 bg-white px-3 text-xs font-semibold text-brand-600 hover:bg-brand-50">
        + Thêm cột
      </button>

      {/* Export */}
      <ExportButton
        url={ENDPOINTS.reports.kinhDoanh.exportExcel}
        payload={() => ({ rows: [], col_headers: [], bp: selectedBP })}
        filename="BaoCaoKD.xlsx"
        disabled={!columns.some((c) => c.loaded)}
      />
    </>
  )

  // ─── Mobile Bottom Sheets ───
  const sheets = {
    filter: {
      title: 'Bộ lọc',
      content: (
        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-xs font-bold uppercase text-surface-4">Bộ phận</label>
            <select
              value={selectedBP}
              onChange={(e) => setSelectedBP(e.target.value)}
              className="h-10 w-full rounded-lg border border-surface-2 px-3 text-sm"
            >
              {reportData.allowedBP.length > 1 && <option value="">Tất cả BP</option>}
              {reportData.allowedBP.map((bp) => (
                <option key={bp} value={bp}>{bp}</option>
              ))}
            </select>
          </div>
        </div>
      ),
    },
    columns: {
      title: 'Quản lý cột',
      content: (
        <div className="space-y-3">
          {columns.map((col, ci) => (
            <div key={col.id} className="rounded-lg border border-surface-2 p-3">
              <div className="mb-2 text-xs font-bold uppercase text-brand-600">{col.label}</div>
              <div className="flex gap-2">
                <input type="date" defaultValue={col.dateA} className="flex-1 rounded-md border border-surface-2 px-2 py-2 text-xs" />
                {col.type !== 'cn' && (
                  <>
                    <span className="self-center text-surface-3">→</span>
                    <input type="date" defaultValue={col.dateB} className="flex-1 rounded-md border border-surface-2 px-2 py-2 text-xs" />
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      ),
    },
    actions: {
      title: 'Thao tác',
      content: (
        <div className="space-y-2">
          <button className="flex w-full items-center gap-3 rounded-lg border border-surface-2 bg-white p-3 text-sm font-semibold">
            {allExpanded ? 'Thu gọn' : 'Mở rộng'}
          </button>
          <button className="flex w-full items-center gap-3 rounded-lg border border-surface-2 bg-white p-3 text-sm font-semibold">
            Tải lại
          </button>
          <button className="flex w-full items-center gap-3 rounded-lg border border-emerald-500 bg-white p-3 text-sm font-semibold text-emerald-700">
            Xuất Excel
          </button>
        </div>
      ),
    },
  }

  return (
    <ReportShell toolbar={toolbar} sheets={sheets}>
      {/* TODO: Render TreeTable with columns data */}
      <div className="flex h-full items-center justify-center text-surface-4">
        <div className="text-center">
          <p className="text-lg font-bold">Báo cáo Kinh Doanh</p>
          <p className="mt-2 text-sm">
            ✓ Layout skeleton hoàn chỉnh<br />
            ✓ {reportData.roots.length} root NV nodes loaded<br />
            ✓ {reportData.khMap.size} khách hàng loaded<br />
            ✓ {reportData.allowedNV.size} NV allowed (RLS)<br />
            ✓ {reportData.allowedBP.length} BP available<br />
            <br />
            TODO: Render TreeTable + load column data
          </p>
        </div>
      </div>
    </ReportShell>
  )
}
