import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@shared/api/client'
import { ENDPOINTS } from '@shared/api/endpoints'
import { useAuth } from '@shared/auth/AuthProvider'

// ============================================================================
// DashboardListPage — Grid of dashboard cards
//
// Loads from GET /api/dashboards (Flask).
// Falls back to mock data when API unavailable (dev without backend).
// Card style: white card, gradient SVG icon offset top-left, accent left stripe on hover.
// ============================================================================

interface DashboardItem {
  id: number
  slug: string
  name: string
  description: string
  dashboard_type: string
  powerbi_url: string
  sort_order: number
  icon_svg: string
  color: string
}

/** Map dashboard_type + slug to a route */
function getDashboardRoute(d: DashboardItem): string {
  if (d.dashboard_type === 'report') {
    return '/r/' + d.slug
  }
  if (d.dashboard_type === 'analytics') {
    return '/r/analytics'
  }
  // powerbi or default
  return '/d/' + d.slug
}

/** Color token map */
const COLORS: Record<string, { accent: string; badgeBg: string; grad: string; sh: string }> = {
  teal:    { accent: '#0d9488', badgeBg: '#f0fdfa', grad: 'linear-gradient(180deg,#14b8a6,#0d9488)', sh: 'rgba(13,148,136,.13)' },
  blue:    { accent: '#1a46c4', badgeBg: '#eef2ff', grad: 'linear-gradient(180deg,#60a5fa,#1a46c4)', sh: 'rgba(26,70,196,.13)' },
  purple:  { accent: '#7c3aed', badgeBg: '#f5f3ff', grad: 'linear-gradient(180deg,#c084fc,#7c3aed)', sh: 'rgba(124,58,237,.13)' },
  amber:   { accent: '#d97706', badgeBg: '#fffbeb', grad: 'linear-gradient(180deg,#fbbf24,#d97706)', sh: 'rgba(217,119,6,.13)' },
  rose:    { accent: '#e11d48', badgeBg: '#fff1f2', grad: 'linear-gradient(180deg,#fb7185,#e11d48)', sh: 'rgba(225,29,72,.13)' },
  emerald: { accent: '#059669', badgeBg: '#ecfdf5', grad: 'linear-gradient(180deg,#34d399,#059669)', sh: 'rgba(5,150,105,.13)' },
  indigo:  { accent: '#4f46e5', badgeBg: '#eef2ff', grad: 'linear-gradient(180deg,#818cf8,#4f46e5)', sh: 'rgba(79,70,229,.13)' },
  cyan:    { accent: '#0891b2', badgeBg: '#ecfeff', grad: 'linear-gradient(180deg,#22d3ee,#0891b2)', sh: 'rgba(8,145,178,.13)' },
}

/** Default icon per dashboard_type when icon_svg is empty */
const DEFAULT_ICONS: Record<string, string> = {
  report: `<svg viewBox="0 0 52 52" fill="none"><rect x="8" y="4" width="36" height="44" rx="6" fill="currentFill" stroke="currentStroke" stroke-width="2"/><rect x="14" y="16" width="24" height="2.5" rx="1.2" fill="currentStroke" opacity=".2"/><rect x="14" y="22" width="20" height="2.5" rx="1.2" fill="currentStroke" opacity=".15"/><rect x="14" y="28" width="22" height="2.5" rx="1.2" fill="currentStroke" opacity=".1"/><rect x="14" y="34" width="18" height="2.5" rx="1.2" fill="currentStroke" opacity=".08"/></svg>`,
  powerbi: `<svg viewBox="0 0 52 52" fill="none"><rect x="4" y="6" width="44" height="36" rx="6" fill="currentFill" stroke="currentStroke" stroke-width="2"/><rect x="8" y="10" width="18" height="14" rx="3" fill="currentStroke" opacity=".1"/><rect x="30" y="10" width="14" height="6" rx="2" fill="currentStroke" opacity=".12"/><rect x="30" y="19" width="14" height="5" rx="2" fill="currentStroke" opacity=".08"/><rect x="11" y="18" width="3" height="4" rx="1" fill="currentStroke" opacity=".25"/><rect x="16" y="15" width="3" height="7" rx="1" fill="currentStroke" opacity=".3"/><rect x="21" y="12" width="3" height="10" rx="1" fill="currentStroke" opacity=".2"/><rect x="8" y="28" width="36" height="6" rx="2" fill="currentStroke" opacity=".07"/><line x1="20" y1="44" x2="32" y2="44" stroke="currentStroke" stroke-width="2" stroke-linecap="round" opacity=".2"/><line x1="26" y1="42" x2="26" y2="44" stroke="currentStroke" stroke-width="1.5" opacity=".2"/></svg>`,
  analytics: `<svg viewBox="0 0 52 52" fill="none"><path d="M4 40L12 28l8 6 8-14 8 4 8-12v28H4z" fill="currentFill"/><polyline points="4,40 12,28 20,34 28,20 36,24 44,12" stroke="currentStroke" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/><circle cx="12" cy="28" r="2.5" fill="#fff" stroke="currentStroke" stroke-width="2"/><circle cx="28" cy="20" r="2.5" fill="#fff" stroke="currentStroke" stroke-width="2"/><circle cx="44" cy="12" r="3" fill="#fff" stroke="currentStroke" stroke-width="2"/></svg>`,
}

/** Badge text per type */
const TYPE_LABELS: Record<string, string> = {
  report: 'REPORT',
  powerbi: 'POWER BI',
  analytics: 'ANALYTICS',
}

export default function DashboardListPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [dashboards, setDashboards] = useState<DashboardItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const res = await apiClient.get<{ success: boolean; data: DashboardItem[] }>(
          ENDPOINTS.dashboard.apiList
        )
        if (!cancelled && res.success) setDashboards(res.data)
      } catch {
        if (!cancelled) {
          console.warn('Dashboard API failed, using mock data')
          setDashboards(MOCK_DASHBOARDS)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  function getColorVars(color: string) {
    return COLORS[color] || COLORS.teal
  }

  function renderIcon(d: DashboardItem) {
    // If dashboard has custom icon_svg, use it
    if (d.icon_svg) {
      return <div className="db-card-icon" dangerouslySetInnerHTML={{ __html: d.icon_svg }} />
    }
    // Otherwise use default per type
    const svg = DEFAULT_ICONS[d.dashboard_type] || DEFAULT_ICONS.report
    return <div className="db-card-icon" dangerouslySetInnerHTML={{ __html: svg }} />
  }

  return (
    <div className="db-list">
      <div className="db-list-header">
        <h1 className="db-list-title">Dashboard</h1>
        <p className="db-list-sub">
          {user?.displayName ? `Xin chao, ${user.displayName}` : 'Chon bao cao hoac dashboard de bat dau'}
        </p>
      </div>

      {loading ? (
        <div className="db-list-loading">Dang tai...</div>
      ) : dashboards.length === 0 ? (
        <div className="db-list-empty">Khong co dashboard nao duoc phan quyen</div>
      ) : (
        <div className="db-grid">
          {dashboards.map((d) => {
            const c = getColorVars(d.color)
            return (
              <div
                key={d.id}
                className="db-card"
                style={{
                  '--accent': c.accent,
                  '--badge-bg': c.badgeBg,
                  '--grad': c.grad,
                  '--sh': c.sh,
                  '--fill': c.badgeBg,
                  '--stroke': c.accent,
                } as React.CSSProperties}
                onClick={() => navigate(getDashboardRoute(d))}
              >
                {renderIcon(d)}
                <div className="db-card-body">
                  <div className="db-card-name">{d.name}</div>
                  <div className="db-card-desc">{d.description}</div>
                </div>
                <div className="db-card-foot">
                  <div className="db-card-meta">
                    <span className="db-card-badge">{TYPE_LABELS[d.dashboard_type] || 'DASHBOARD'}</span>
                  </div>
                  <div className="db-card-go">
                    <svg viewBox="0 0 16 16"><path d="M6 4l4 4-4 4"/></svg>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ═══ Mock data ═══
const MOCK_DASHBOARDS: DashboardItem[] = [
  { id: 1, slug: 'bao-cao-khach-hang', name: 'Bao cao Khach hang', description: 'Cong no, doanh so, doanh thu theo khach hang. Drill-down lich su giao dich.', dashboard_type: 'report', powerbi_url: '', sort_order: 1, icon_svg: '', color: 'teal' },
  { id: 2, slug: 'bao-cao-kinh-doanh', name: 'Bao cao Kinh doanh', description: 'Tong hop kinh doanh theo nhan vien phan cap. Cong no, doanh so, doanh thu.', dashboard_type: 'report', powerbi_url: '', sort_order: 2, icon_svg: '', color: 'blue' },
  { id: 3, slug: 'bao-cao-chi-tiet', name: 'Bao cao Chi tiet', description: 'Chi tiet giao dich ban ra, thanh toan. Du lieu tung dong san pham.', dashboard_type: 'report', powerbi_url: '', sort_order: 3, icon_svg: '', color: 'purple' },
  { id: 4, slug: 'bao-cao-ban-ra', name: 'Bao cao Ban ra', description: 'Bang ke chi tiet xuat ban. Loc theo ngay, san pham, khach hang.', dashboard_type: 'report', powerbi_url: '', sort_order: 4, icon_svg: '', color: 'indigo' },
  { id: 5, slug: 'bao-cao-kpi', name: 'KPI', description: 'Theo doi KPI nhan vien kinh doanh. Muc tieu, hoan thanh, xep hang.', dashboard_type: 'report', powerbi_url: '', sort_order: 5, icon_svg: '', color: 'rose' },
  { id: 6, slug: 'bao-cao-nguyen-lieu', name: 'Nguyen lieu San xuat', description: 'Ton kho, xuat nhap nguyen lieu. Bao cao theo thang va lo san xuat.', dashboard_type: 'report', powerbi_url: '', sort_order: 6, icon_svg: '', color: 'emerald' },
  { id: 7, slug: 'tong-quan', name: 'Dashboard Tong quan', description: 'Power BI tong hop kinh doanh, du no, KPI. Cap nhat tu dong.', dashboard_type: 'powerbi', powerbi_url: 'https://app.powerbi.com/...', sort_order: 7, icon_svg: '', color: 'amber' },
  { id: 8, slug: 'analytics', name: 'Analytics', description: 'Thong ke truy cap, hoat dong nguoi dung, xu huong su dung he thong.', dashboard_type: 'analytics', powerbi_url: '', sort_order: 8, icon_svg: '', color: 'cyan' },
]