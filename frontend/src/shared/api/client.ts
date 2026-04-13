/**
 * API Client — thin wrapper around fetch with:
 * - Base URL config
 * - Auth headers (session-based, cookie)
 * - Standardized error handling
 * - Type-safe responses
 */

const API_BASE = '' // Same origin — Flask serves both API and React build

interface RequestOptions extends RequestInit {
  params?: Record<string, string>
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(url: string, options: RequestOptions = {}): Promise<T> {
  const { params, ...fetchOptions } = options

  // Build URL with query params
  let fullUrl = `${API_BASE}${url}`
  if (params) {
    const searchParams = new URLSearchParams(params)
    fullUrl += `?${searchParams.toString()}`
  }

  // Default headers
  const headers = new Headers(fetchOptions.headers)
  if (!headers.has('Content-Type') && fetchOptions.body && typeof fetchOptions.body === 'string') {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(fullUrl, {
    ...fetchOptions,
    headers,
    credentials: 'same-origin', // Send session cookie
  })

  // Redirect to login on 401/403
  if (response.status === 401 || response.status === 403) {
    window.location.href = '/login'
    throw new ApiError(response.status, 'Unauthorized')
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new ApiError(
      response.status,
      (errorData as { error?: string }).error || `HTTP ${response.status}`,
      errorData,
    )
  }

  return response.json() as Promise<T>
}

export const apiClient = {
  get: <T>(url: string, params?: Record<string, string>) =>
    request<T>(url, { method: 'GET', params }),

  post: <T>(url: string, body: unknown) =>
    request<T>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  /** POST that returns a Blob (for file downloads) */
  postBlob: async (url: string, body: unknown): Promise<{ blob: Blob; filename: string }> => {
    const response = await fetch(`${API_BASE}${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      credentials: 'same-origin',
    })
    if (!response.ok) throw new ApiError(response.status, `HTTP ${response.status}`)
    const blob = await response.blob()
    const cd = response.headers.get('Content-Disposition')
    const filename = cd?.match(/filename=(.+)/)?.[1]?.replace(/"/g, '') || 'export.xlsx'
    return { blob, filename }
  },
}

export { ApiError }
