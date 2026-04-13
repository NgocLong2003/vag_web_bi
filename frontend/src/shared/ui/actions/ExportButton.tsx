import { FileSpreadsheet, FileText, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { apiClient } from '@shared/api/client'
import { toast } from '@shared/ui/feedback/Toast'

// ============================================================================
// STANDARDS: Tải Xuống
// - Mọi trang báo cáo đều phải có: Excel (phân tích) + PDF (in ấn)
// - ExportBar luôn render cả 2 nút
// ============================================================================

interface ExportEndpoint {
  url: string
  payload: () => unknown
  filename?: string
}

interface ExportBarProps {
  /** Excel export config */
  excel: ExportEndpoint
  /** PDF export config */
  pdf: ExportEndpoint
  /** Disabled state (e.g. when no data) */
  disabled?: boolean
}

/**
 * ExportBar — thanh tải xuống chuẩn cho mọi trang báo cáo.
 * Luôn hiển thị cả Excel + PDF.
 */
export function ExportBar({ excel, pdf, disabled = false }: ExportBarProps) {
  const [loadingExcel, setLoadingExcel] = useState(false)
  const [loadingPdf, setLoadingPdf] = useState(false)

  async function handleDownload(
    config: ExportEndpoint,
    setLoading: (v: boolean) => void,
    label: string
  ) {
    if (disabled) return
    setLoading(true)
    try {
      const { blob, filename: serverFilename } = await apiClient.postBlob(
        config.url,
        config.payload()
      )
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = serverFilename || config.filename || `export.${label === 'Excel' ? 'xlsx' : 'pdf'}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(objectUrl)
      toast(`Đã tải ${label}`)
    } catch (e) {
      toast((e as Error).message, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      {/* Excel button */}
      <button
        onClick={() => handleDownload(excel, setLoadingExcel, 'Excel')}
        disabled={loadingExcel || disabled}
        className="flex h-8 items-center gap-1.5 rounded-md border border-emerald-500 bg-white px-3 text-xs font-semibold text-emerald-700 transition-colors hover:bg-emerald-50 disabled:opacity-50"
      >
        {loadingExcel ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <FileSpreadsheet className="h-3.5 w-3.5" />
        )}
        Excel
      </button>

      {/* PDF button */}
      <button
        onClick={() => handleDownload(pdf, setLoadingPdf, 'PDF')}
        disabled={loadingPdf || disabled}
        className="flex h-8 items-center gap-1.5 rounded-md border border-red-400 bg-white px-3 text-xs font-semibold text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50"
      >
        {loadingPdf ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <FileText className="h-3.5 w-3.5" />
        )}
        PDF
      </button>
    </div>
  )
}

// Re-export single button for edge cases (e.g. admin page only needs Excel)
export { ExportBar as ExportButton }

