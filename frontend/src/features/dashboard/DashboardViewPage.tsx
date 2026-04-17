import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiClient } from '@shared/api/client'
import { ENDPOINTS } from '@shared/api/endpoints'

// ============================================================================
// DashboardViewPage — Renders a single dashboard by slug
//
// For powerbi type: fetches report URL, renders iframe
// For report type: redirects to /r/:slug (React report page)
// For analytics type: redirects to /r/analytics
// ============================================================================

interface DashboardDetail {
  id: number
  slug: string
  name: string
  dashboard_type: string
  powerbi_url: string
}

export default function DashboardViewPage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState<DashboardDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!slug) return
    let cancelled = false

    async function load() {
      try {
        // Load all dashboards and find by slug
        const res = await apiClient.get<{ success: boolean; data: DashboardDetail[] }>(
          ENDPOINTS.dashboard.apiList
        )
        if (cancelled) return
        if (!res.success) { setError('API error'); setLoading(false); return }

        const found = res.data.find((d) => d.slug === slug)
        if (!found) { setError('Dashboard khong ton tai hoac ban khong co quyen'); setLoading(false); return }

        // Route based on type
        if (found.dashboard_type === 'report') {
          navigate('/r/' + found.slug, { replace: true })
          return
        }
        if (found.dashboard_type === 'analytics') {
          navigate('/r/analytics', { replace: true })
          return
        }

        // powerbi — render iframe
        setDashboard(found)
      } catch (e) {
        if (!cancelled) setError((e as Error).message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [slug, navigate])

  if (loading) {
    return <div className="db-view-status">Dang tai...</div>
  }

  if (error) {
    return (
      <div className="db-view-status">
        <div className="db-view-error">{error}</div>
        <button className="db-view-back" onClick={() => navigate('/dashboards')}>
          Quay lai danh sach
        </button>
      </div>
    )
  }

  if (!dashboard) return null

  // Decode Power BI URL if obfuscated (base64)
  let iframeUrl = dashboard.powerbi_url
  try {
    if (iframeUrl && !iframeUrl.startsWith('http')) {
      iframeUrl = atob(iframeUrl)
    }
  } catch {
    // Not base64, use as-is
  }

  return (
    <div className="db-view">
      {iframeUrl ? (
        <iframe
          className="db-view-iframe"
          src={iframeUrl}
          frameBorder="0"
          allowFullScreen
          title={dashboard.name}
        />
      ) : (
        <div className="db-view-status">
          <div className="db-view-error">URL Power BI chua duoc cau hinh</div>
          <button className="db-view-back" onClick={() => navigate('/dashboards')}>
            Quay lai danh sach
          </button>
        </div>
      )}
    </div>
  )
}