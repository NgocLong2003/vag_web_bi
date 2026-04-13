import { apiClient } from '@shared/api/client'

/**
 * Download Excel file from API.
 * POST JSON payload → receive blob → trigger download.
 */
export async function downloadExcel(
  url: string,
  payload: unknown,
  fallbackFilename = 'export.xlsx',
): Promise<void> {
  const { blob, filename } = await apiClient.postBlob(url, payload)
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = filename || fallbackFilename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(objectUrl)
}

/**
 * Open URL in new tab (for server-generated Excel downloads via GET).
 */
export function downloadUrl(url: string): void {
  window.open(url, '_blank')
}
