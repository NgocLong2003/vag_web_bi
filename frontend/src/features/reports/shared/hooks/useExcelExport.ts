// ============================================================================
// useExcelExport — Gọi API export Excel + download file
// Dùng chung cho mọi báo cáo
// ============================================================================

import { useState, useCallback } from 'react'
import { apiClient } from '@shared/api/client'

interface ExportState {
  exporting: boolean
  error: string
}

export function useExcelExport() {
  const [state, setState] = useState<ExportState>({ exporting: false, error: '' })

  const exportExcel = useCallback(async (
    url: string,
    payload: unknown,
    defaultFilename = 'export.xlsx',
  ) => {
    setState({ exporting: true, error: '' })
    try {
      const { blob, filename } = await apiClient.postBlob(url, payload)
      // Download
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename || defaultFilename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(a.href)
      setState({ exporting: false, error: '' })
      return true
    } catch (e: any) {
      setState({ exporting: false, error: e.message || String(e) })
      return false
    }
  }, [])

  return { ...state, exportExcel }
}