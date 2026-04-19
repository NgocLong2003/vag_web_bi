import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@shared/api/client'
import { ENDPOINTS } from '@shared/api/endpoints'
import { useAuth } from '@shared/auth/AuthProvider'

interface DashboardItem {
  id: number; slug: string; name: string; description: string
  dashboard_type: string; powerbi_url: string; sort_order: number
  category: string; icon_svg: string; color: string
  update_mode: string; update_interval: string; updated_at: string
}

function getDashboardRoute(d: DashboardItem): string {
  if (d.dashboard_type === 'report') return '/r/' + d.slug
  if (d.dashboard_type === 'analytics') return '/r/analytics'
  return '/d/' + d.slug
}

function timeAgo(dateStr: string): string {
  if (!dateStr || dateStr === 'None' || dateStr === '') return ''
  try {
    const diff = Date.now() - new Date(dateStr).getTime()
    const m = Math.floor(diff / 60000)
    if (m < 1) return 'vừa xong'
    if (m < 60) return m + ' phút trước'
    const h = Math.floor(m / 60)
    if (h < 24) return h + ' giờ trước'
    return Math.floor(h / 24) + ' ngày trước'
  } catch { return '' }
}

const COLORS: Record<string, { accent: string; badgeBg: string; grad: string; sh: string; fill: string }> = {
  teal:    { accent:'#0d9488', badgeBg:'#f0fdfa', grad:'linear-gradient(180deg,#14b8a6,#0d9488)', sh:'rgba(13,148,136,.13)', fill:'#f0fdfa' },
  blue:    { accent:'#1a46c4', badgeBg:'#eef2ff', grad:'linear-gradient(180deg,#60a5fa,#1a46c4)', sh:'rgba(26,70,196,.13)', fill:'#eef2ff' },
  purple:  { accent:'#7c3aed', badgeBg:'#f5f3ff', grad:'linear-gradient(180deg,#c084fc,#7c3aed)', sh:'rgba(124,58,237,.13)', fill:'#f5f3ff' },
  amber:   { accent:'#d97706', badgeBg:'#fffbeb', grad:'linear-gradient(180deg,#fbbf24,#d97706)', sh:'rgba(217,119,6,.13)', fill:'#fffbeb' },
  rose:    { accent:'#e11d48', badgeBg:'#fff1f2', grad:'linear-gradient(180deg,#fb7185,#e11d48)', sh:'rgba(225,29,72,.13)', fill:'#fff1f2' },
  emerald: { accent:'#059669', badgeBg:'#ecfdf5', grad:'linear-gradient(180deg,#34d399,#059669)', sh:'rgba(5,150,105,.13)', fill:'#ecfdf5' },
  indigo:  { accent:'#4f46e5', badgeBg:'#eef2ff', grad:'linear-gradient(180deg,#818cf8,#4f46e5)', sh:'rgba(79,70,229,.13)', fill:'#eef2ff' },
  cyan:    { accent:'#0891b2', badgeBg:'#ecfeff', grad:'linear-gradient(180deg,#22d3ee,#0891b2)', sh:'rgba(8,145,178,.13)', fill:'#ecfeff' },
}

const DEFAULT_ICONS: Record<string, string> = {
  report: '<svg viewBox="0 0 52 52" fill="none"><rect x="8" y="4" width="36" height="44" rx="6" fill="currentFill" stroke="currentStroke" stroke-width="2"/><rect x="14" y="16" width="24" height="2.5" rx="1.2" fill="currentStroke" opacity=".2"/><rect x="14" y="22" width="20" height="2.5" rx="1.2" fill="currentStroke" opacity=".15"/><rect x="14" y="28" width="22" height="2.5" rx="1.2" fill="currentStroke" opacity=".1"/></svg>',
  powerbi: '<svg viewBox="0 0 52 52" fill="none"><rect x="4" y="6" width="44" height="36" rx="6" fill="currentFill" stroke="currentStroke" stroke-width="2"/><rect x="11" y="18" width="3" height="4" rx="1" fill="currentStroke" opacity=".25"/><rect x="16" y="15" width="3" height="7" rx="1" fill="currentStroke" opacity=".3"/><rect x="21" y="12" width="3" height="10" rx="1" fill="currentStroke" opacity=".2"/><rect x="8" y="28" width="36" height="6" rx="2" fill="currentStroke" opacity=".07"/><line x1="20" y1="44" x2="32" y2="44" stroke="currentStroke" stroke-width="2" stroke-linecap="round" opacity=".2"/><line x1="26" y1="42" x2="26" y2="44" stroke="currentStroke" stroke-width="1.5" opacity=".2"/></svg>',
  analytics: '<svg viewBox="0 0 52 52" fill="none"><path d="M4 40L12 28l8 6 8-14 8 4 8-12v28H4z" fill="currentFill"/><polyline points="4,40 12,28 20,34 28,20 36,24 44,12" stroke="currentStroke" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/><circle cx="28" cy="20" r="2.5" fill="#fff" stroke="currentStroke" stroke-width="2"/><circle cx="44" cy="12" r="3" fill="#fff" stroke="currentStroke" stroke-width="2"/></svg>',
}

/** SVG nhỏ cho status badge */
const LIVE_ICON = '<svg viewBox="0 0 16 16" fill="none" width="12" height="12"><circle cx="8" cy="8" r="3" fill="#10b981"/><circle cx="8" cy="8" r="6" stroke="#10b981" stroke-width="1.5" opacity=".3"/><circle cx="8" cy="8" r="6" stroke="#10b981" stroke-width="1.5" opacity=".15"><animate attributeName="r" values="5;8;5" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".3;0;.3" dur="2s" repeatCount="indefinite"/></circle></svg>'
const SCHED_ICON = '<svg viewBox="0 0 16 16" fill="none" width="12" height="12"><circle cx="8" cy="8" r="6.5" stroke="#94a3b8" stroke-width="1.3"/><path d="M8 4.5V8l2.5 1.5" stroke="#94a3b8" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>'

export default function DashboardListPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [dashboards, setDashboards] = useState<DashboardItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const res = await apiClient.get<{ success: boolean; data: DashboardItem[] }>(ENDPOINTS.dashboard.apiList)
        if (!cancelled) {
          if (res.success && res.data) setDashboards(res.data)
          else setError('Không tải được danh sách dashboard')
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.status === 401 ? 'Chưa đăng nhập' : 'Không kết nối được API')
      } finally { if (!cancelled) setLoading(false) }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const grouped = useMemo(() => {
    const map = new Map<string, DashboardItem[]>()
    dashboards.forEach((d) => {
      const cat = d.category || 'Khác'
      if (!map.has(cat)) map.set(cat, [])
      map.get(cat)!.push(d)
    })
    return Array.from(map.entries())
  }, [dashboards])

  function renderIcon(d: DashboardItem) {
    const svg = d.icon_svg || DEFAULT_ICONS[d.dashboard_type] || DEFAULT_ICONS.report
    return <div className="db-card-icon" dangerouslySetInnerHTML={{ __html: svg }} />
  }

  function renderStatusBadge(d: DashboardItem) {
    if (d.update_mode === 'realtime') {
      return (
        <div className="db-badge db-badge-live">
          <span dangerouslySetInnerHTML={{ __html: LIVE_ICON }} />
          <span>Real-time</span>
        </div>
      )
    }
    const label = d.update_interval || 'Định kỳ'
    return (
      <div className="db-badge db-badge-sched">
        <span dangerouslySetInnerHTML={{ __html: SCHED_ICON }} />
        <span>{label}</span>
      </div>
    )
  }

  return (
    <div className="db-list">
      {/* SVG gradient defs */}
      <svg width="0" height="0" style={{ position: 'absolute' }}>
        <defs>
          <linearGradient id="st" x1="0" y1="1" x2=".8" y2="0"><stop offset="0%" stopColor="#14b8a6"/><stop offset="100%" stopColor="#0d9488"/></linearGradient>
          <linearGradient id="sb" x1="0" y1="1" x2=".8" y2="0"><stop offset="0%" stopColor="#60a5fa"/><stop offset="100%" stopColor="#1a46c4"/></linearGradient>
          <linearGradient id="sp" x1="0" y1="1" x2=".8" y2="0"><stop offset="0%" stopColor="#c084fc"/><stop offset="100%" stopColor="#7c3aed"/></linearGradient>
          <linearGradient id="sa" x1="0" y1="1" x2=".8" y2="0"><stop offset="0%" stopColor="#fbbf24"/><stop offset="100%" stopColor="#d97706"/></linearGradient>
          <linearGradient id="sr" x1="0" y1="1" x2=".8" y2="0"><stop offset="0%" stopColor="#fb7185"/><stop offset="100%" stopColor="#e11d48"/></linearGradient>
          <linearGradient id="se" x1="0" y1="1" x2=".8" y2="0"><stop offset="0%" stopColor="#34d399"/><stop offset="100%" stopColor="#059669"/></linearGradient>
          <linearGradient id="si" x1="0" y1="1" x2=".8" y2="0"><stop offset="0%" stopColor="#818cf8"/><stop offset="100%" stopColor="#4f46e5"/></linearGradient>
          <linearGradient id="sc" x1="0" y1="1" x2=".8" y2="0"><stop offset="0%" stopColor="#22d3ee"/><stop offset="100%" stopColor="#0891b2"/></linearGradient>
          <linearGradient id="ft" x1="0" y1="1" x2=".3" y2="0"><stop offset="0%" stopColor="#14b8a6" stopOpacity=".18"/><stop offset="100%" stopColor="#0d9488" stopOpacity=".03"/></linearGradient>
          <linearGradient id="fb" x1="0" y1="1" x2=".3" y2="0"><stop offset="0%" stopColor="#60a5fa" stopOpacity=".18"/><stop offset="100%" stopColor="#1a46c4" stopOpacity=".03"/></linearGradient>
          <linearGradient id="fp" x1="0" y1="1" x2=".3" y2="0"><stop offset="0%" stopColor="#c084fc" stopOpacity=".18"/><stop offset="100%" stopColor="#7c3aed" stopOpacity=".03"/></linearGradient>
          <linearGradient id="fa" x1="0" y1="1" x2=".3" y2="0"><stop offset="0%" stopColor="#fbbf24" stopOpacity=".18"/><stop offset="100%" stopColor="#d97706" stopOpacity=".03"/></linearGradient>
          <linearGradient id="fr" x1="0" y1="1" x2=".3" y2="0"><stop offset="0%" stopColor="#fb7185" stopOpacity=".18"/><stop offset="100%" stopColor="#e11d48" stopOpacity=".03"/></linearGradient>
          <linearGradient id="fe" x1="0" y1="1" x2=".3" y2="0"><stop offset="0%" stopColor="#34d399" stopOpacity=".18"/><stop offset="100%" stopColor="#059669" stopOpacity=".03"/></linearGradient>
          <linearGradient id="fi" x1="0" y1="1" x2=".3" y2="0"><stop offset="0%" stopColor="#818cf8" stopOpacity=".18"/><stop offset="100%" stopColor="#4f46e5" stopOpacity=".03"/></linearGradient>
          <linearGradient id="fc" x1="0" y1="1" x2=".3" y2="0"><stop offset="0%" stopColor="#22d3ee" stopOpacity=".18"/><stop offset="100%" stopColor="#0891b2" stopOpacity=".03"/></linearGradient>
        </defs>
      </svg>

      {/* Header */}
      <div className="db-list-header">
        <h1 className="db-list-title">Dashboard</h1>
        <p className="db-list-sub">
          {user?.displayName
            ? <>Xin chào, <strong>{user.displayName}</strong>. Chọn báo cáo để bắt đầu.</>
            : 'Chọn báo cáo hoặc dashboard để bắt đầu.'}
        </p>
      </div>

      {loading ? (
        <div className="db-list-loading">
          <div className="db-spinner" />
          <span>Đang tải danh sách...</span>
        </div>
      ) : error ? (
        <div className="db-list-error">
          <div className="db-list-error-text">{error}</div>
          <div className="db-list-error-hint">Mở F12 → Console để xem chi tiết lỗi.</div>
        </div>
      ) : dashboards.length === 0 ? (
        <div className="db-list-empty">Không có dashboard nào được phân quyền cho bạn.</div>
      ) : (
        grouped.map(([category, items], gi) => (
          <div key={category} className="db-category">
            {/* Tiêu đề phân loại */}
            <div className="db-category-header">
              <span className="db-category-dot" />
              <h2 className="db-category-title">{category}</h2>
              <span className="db-category-count">{items.length}</span>
            </div>

            <div className="db-grid">
              {items.map((d) => {
                const c = COLORS[d.color] || COLORS.teal
                return (
                  <div
                    key={d.id}
                    className="db-card"
                    style={{
                      '--accent': c.accent, '--badge-bg': c.badgeBg,
                      '--grad': c.grad, '--sh': c.sh,
                      '--fill': c.fill, '--stroke': c.accent,
                    } as React.CSSProperties}
                    onClick={() => navigate(getDashboardRoute(d))}
                  >
                    {/* Icon trái trên — offset */}
                    {renderIcon(d)}

                    {/* Status badge phải trên — offset */}
                    <div className="db-card-status">{renderStatusBadge(d)}</div>

                    {/* Nội dung */}
                    <div className="db-card-body">
                      <div className="db-card-name">{d.name}</div>
                      {d.description && <div className="db-card-desc">{d.description}</div>}
                    </div>

                    {/* Footer */}
                    <div className="db-card-foot">
                      <span className="db-card-type">{d.dashboard_type === 'powerbi' ? 'Power BI' : d.dashboard_type === 'analytics' ? 'Analytics' : 'Báo cáo'}</span>
                      {d.update_mode !== 'realtime' && timeAgo(d.updated_at) && (
                        <span className="db-card-ago">Cập nhật {timeAgo(d.updated_at)}</span>
                      )}
                      <div className="db-card-go">
                        <svg viewBox="0 0 16 16"><path d="M6 4l4 4-4 4"/></svg>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))
      )}
    </div>
  )
}