import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@shared/auth/AuthProvider'
import { useReportStore } from '@shared/stores/useReportStore'
import { SettingsModal } from '@shared/ui/modals/SettingsModal'
import { HelpModal } from '@shared/ui/modals/HelpModal'
import {
  Star,
  Bell,
  Download,
  Maximize,
  Minimize,
  ChevronDown,
  Settings,
  Shield,
  HelpCircle,
  LogOut,
} from 'lucide-react'
import { useState, useRef, useEffect, useCallback } from 'react'

// ============================================================================
// HEADER — Split-pill floating header (desktop only)
//
// Left pill:  Logo (Home) | Dashboard selector | Update badge
// Right pill: Hỏi AI | Cảnh báo | Tải xuống (split) | Toàn màn hình | Avatar
//
// STANDARDS:
// - Tất cả nút đều có text label (user không hiểu icon-only)
// - Tải xuống: split button (main = default format, dropdown = other formats)
// - Real-time: không có dropdown. Scheduled: có dropdown lịch sử cập nhật
// - Mỗi nút có ring glow effect riêng khi hover
// ============================================================================

export interface DashboardOption {
  id: string
  name: string
  group: string
}

export interface UpdateLogEntry {
  time: string
  message: string
  status: 'ok' | 'warn' | 'error'
}

export interface HeaderProps {
  /** Current dashboard/report name */
  dashboardName?: string
  /** Available dashboards for selector dropdown */
  dashboards?: DashboardOption[]
  /** Data update mode */
  updateMode?: 'realtime' | 'scheduled'
  /** For scheduled: display text e.g. "5 phút trước" */
  lastUpdateText?: string
  /** For scheduled: update history log */
  updateLog?: UpdateLogEntry[]
  /** Default download format when clicking main button */
  defaultDownloadFormat?: 'xlsx' | 'pdf' | 'csv'
  /** Called when user downloads */
  onDownload?: (format: string) => void
  /** Called when user switches dashboard */
  onDashboardChange?: (id: string) => void
  /** Number of unread alerts (0 = no badge) */
  alertCount?: number
  /** Alert items to render in dropdown */
  alertSlot?: React.ReactNode
}

export function Header({
  dashboardName: propName,
  dashboards: propDashboards = [],
  updateMode: propUpdateMode,
  lastUpdateText: propLastUpdateText,
  updateLog = [],
  defaultDownloadFormat = 'xlsx',
  onDownload,
  onDashboardChange,
  alertCount = 0,
  alertSlot,
}: HeaderProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const isListPage = location.pathname === '/dashboards' || location.pathname === '/'

  // ── Read from store (page sets these on mount) ──
  const storeReportName = useReportStore(s => s.reportName)
  const storeUpdateMode = useReportStore(s => s.updateMode)
  const storeUpdateInterval = useReportStore(s => s.updateInterval)
  const storeLastUpdateText = useReportStore(s => s.lastUpdateText)
  const reportDownloadHandler = useReportStore(s => s.downloadHandler)
  const reportDownloading = useReportStore(s => s.downloading)
  const storeDashboards = useReportStore(s => s.dashboards) as any[]

  // Store overrides props
  const dashboardName = storeReportName || propName || 'Dashboard'
  const updateMode = propUpdateMode || storeUpdateMode || 'realtime'
  const lastUpdateText = propLastUpdateText || storeLastUpdateText || ''
  const updateInterval = storeUpdateInterval || ''
  const dashboards: DashboardOption[] = (storeDashboards.length ? storeDashboards : propDashboards).map((d: any) => ({
    id: d.id?.toString() || d.slug || '',
    name: d.name,
    group: d.group || d.category || 'Khác',
  }))

  const [fullscreen, setFullscreen] = useState(false)
  const [openDD, setOpenDD] = useState<string | null>(null)
  const [dbSearch, setDbSearch] = useState('')
  const [modal, setModal] = useState<'settings' | 'help' | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  const closeAll = useCallback(() => {
    setOpenDD(null)
    setDbSearch('')
  }, [])

  function toggle(id: string) {
    setOpenDD((prev) => (prev === id ? null : id))
  }

  // Close on Escape or click outside
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && closeAll()
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) closeAll()
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('click', onClick)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('click', onClick)
    }
  }, [closeAll])

  // Fullscreen sync
  useEffect(() => {
    const h = () => setFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', h)
    return () => document.removeEventListener('fullscreenchange', h)
  }, [])

  function toggleFullscreen() {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen()
    else document.exitFullscreen()
  }

  // Dashboard filter
  const filtered = dashboards.filter((d) =>
    d.name.toLowerCase().includes(dbSearch.toLowerCase())
  )
  const groups = [...new Set(filtered.map((d) => d.group))]

  // User initials
  const initials = (user?.displayName || user?.username || 'U')
    .split(' ')
    .map((w) => w[0])
    .join('')
    .substring(0, 2)
    .toUpperCase()

  return (
    <>
    <div ref={ref} className="hdr-area">
      {/* ══ LEFT PILL — hidden on dashboard list page ══ */}
      {!isListPage && (
      <div className="pill pill-l">
        {/* Logo = Home */}
        <div
          className="hdr-logo"
          onClick={() => navigate('/dashboards')}
          title="Về trang chủ"
        >
          VA
        </div>

        {/* Dashboard selector */}
        <div className="relative">
          <button
            className={`db-trigger ${openDD === 'db' ? 'open' : ''}`}
            onClick={(e) => { e.stopPropagation(); toggle('db') }}
          >
            <span className="db-name">{dashboardName}</span>
            <ChevronDown className="db-chev" />
          </button>

          {openDD === 'db' && (
            <div className="dropdown show db-dd" onClick={(e) => e.stopPropagation()}>
              <input
                className="db-search"
                placeholder="Tìm dashboard..."
                value={dbSearch}
                onChange={(e) => setDbSearch(e.target.value)}
                autoFocus
              />
              {groups.map((group) => (
                <div key={group}>
                  <div className="db-group">{group}</div>
                  {filtered
                    .filter((d) => d.group === group)
                    .map((d) => (
                      <div
                        key={d.id}
                        className={`db-item ${d.name === dashboardName ? 'active' : ''}`}
                        onClick={() => {
                          // Navigate to dashboard/report
                          const sd = storeDashboards.find((sd: any) => (sd.id?.toString() || sd.slug) === d.id)
                          if (sd) {
                            const slug = (sd as any).slug || ''
                            if ((sd as any).dashboard_type === 'report' && slug) {
                              navigate(`/r/${slug}`)
                            } else if ((sd as any).dashboard_type === 'powerbi' && slug) {
                              navigate(`/d/${slug}`)
                            } else if (slug) {
                              navigate(`/r/${slug}`)
                            }
                          }
                          onDashboardChange?.(d.id)
                          closeAll()
                        }}
                      >
                        {d.name}
                      </div>
                    ))}
                </div>
              ))}
              {filtered.length === 0 && (
                <p className="px-3 py-4 text-center text-xs text-white/30">
                  Không tìm thấy
                </p>
              )}
            </div>
          )}
        </div>

        {/* Update badge */}
        {updateMode === 'realtime' ? (
          <button className="ub-pill realtime" title="Dữ liệu cập nhật real-time">
            <div className="ub-dot" />
            Real-time
          </button>
        ) : (
          <div className="relative">
            <button
              className="ub-pill scheduled"
              onClick={(e) => { e.stopPropagation(); toggle('update') }}
              title="Nhấn để xem lịch sử cập nhật"
            >
              <div className="ub-dot" />
              <div className="ub-text">
                {updateInterval && <span className="ub-interval">{updateInterval}</span>}
                {lastUpdateText && <span className="ub-ago">{lastUpdateText}</span>}
                {!updateInterval && !lastUpdateText && <span>Định kỳ</span>}
              </div>
            </button>
            {openDD === 'update' && (
              <div className="dropdown show ub-modal" onClick={(e) => e.stopPropagation()}>
                <div className="ub-modal-hdr">
                  <span className="ub-modal-title">Lịch sử cập nhật</span>
                </div>
                <div className="ub-modal-list">
                  {updateLog.map((entry, i) => (
                    <div key={i} className="ub-log">
                      <div className={`ub-log-dot ${entry.status === 'ok' ? 'ok' : entry.status === 'warn' ? 'warn' : 'err'}`} />
                      <div className="ub-log-info">
                        <div className="ub-log-time">{entry.time}</div>
                        <div className="ub-log-msg">{entry.message}</div>
                      </div>
                    </div>
                  ))}
                  {updateLog.length === 0 && (
                    <p className="px-3 py-4 text-center text-xs text-white/30">
                      Chưa có lịch sử
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      )}

      {/* ══ RIGHT PILL ══ */}
      <div className="pill pill-r">
        {/* Hỏi AI */}
        <button className="hb hb-ai">
          <Star className="ai-sparkle h-3.5 w-3.5" />
          <span>Hỏi AI</span>
        </button>

        {/* Cảnh báo */}
        <div className="relative">
          <button
            className="hb hb-alert-btn"
            onClick={(e) => { e.stopPropagation(); toggle('alert') }}
          >
            {alertCount > 0 && <div className="alert-dot" />}
            <Bell className="h-3.5 w-3.5" />
            <span>Cảnh báo</span>
          </button>
          {openDD === 'alert' && (
            <div className="dropdown show alert-dd" onClick={(e) => e.stopPropagation()}>
              <div className="alert-dd-hdr">
                <span className="alert-dd-title">Cảnh báo</span>
                {alertCount > 0 && <span className="alert-dd-count">{alertCount} mới</span>}
              </div>
              <div className="alert-list">
                {alertSlot || (
                  <p className="px-3 py-4 text-center text-xs text-white/30">
                    Không có cảnh báo
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Tải xuống — split button */}
        <div className="dl-group relative">
          <button
            className="hb dl-main"
            disabled={reportDownloading}
            onClick={() => {
              const handler = reportDownloadHandler || onDownload
              handler?.(defaultDownloadFormat)
            }}
          >
            <Download className="h-3.5 w-3.5" />
            <span>{reportDownloading ? 'Đang tải...' : 'Tải xuống'}</span>
          </button>
          <button
            className="dl-drop"
            onClick={(e) => { e.stopPropagation(); toggle('dl') }}
          >
            <ChevronDown className="h-3 w-3" />
          </button>
          {openDD === 'dl' && (
            <div className="dropdown show dl-dd" onClick={(e) => e.stopPropagation()}>
              {(['xlsx', 'pdf', 'csv'] as const).map((fmt) => (
                <div
                  key={fmt}
                  className="dl-item"
                  onClick={() => {
                    const handler = reportDownloadHandler || onDownload
                    handler?.(fmt); closeAll()
                  }}
                >
                  <Download className="h-4 w-4" />
                  {fmt === 'xlsx' ? 'Excel' : fmt === 'pdf' ? 'PDF' : 'CSV'}
                  <span className="dl-ext">.{fmt}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Toàn màn hình */}
        <button className="hb hb-fs" onClick={toggleFullscreen}>
          {fullscreen ? <Minimize className="h-3.5 w-3.5" /> : <Maximize className="h-3.5 w-3.5" />}
          <span>{fullscreen ? 'Thoát' : 'Toàn màn hình'}</span>
        </button>

        <div className="h-div" />

        {/* Avatar */}
        <div className="relative">
          <button
            className="av-trigger"
            onClick={(e) => { e.stopPropagation(); toggle('av') }}
          >
            <span className="av-name">{user?.displayName || user?.username}</span>
            <div className="av">{initials}</div>
          </button>
          {openDD === 'av' && (
            <div className="dropdown show av-dd" onClick={(e) => e.stopPropagation()}>
              <div className="av-hdr">
                <div className="av-hdr-name">{user?.displayName}</div>
                <div className="av-hdr-role">{user?.chucVu} · {user?.boPhan}</div>
              </div>
              <div className="av-body">
                <div className="av-item" onClick={() => { closeAll(); setModal('settings') }}>
                  <Settings className="h-4 w-4" /> Cai dat
                </div>
                {user?.role === 'admin' && (
                  <div className="av-item" onClick={() => { closeAll(); navigate('/admin') }}>
                    <Shield className="h-4 w-4" /> Quan tri
                  </div>
                )}
                <div className="av-item" onClick={() => { closeAll(); setModal('help') }}>
                  <HelpCircle className="h-4 w-4" /> Tro giup
                </div>
                <div className="av-divider" />
                <div className="av-item danger" onClick={logout}>
                  <LogOut className="h-4 w-4" /> Dang xuat
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>

    {/* ══ Settings Modal ══ */}
    <SettingsModal open={modal === 'settings'} onClose={() => setModal(null)} />
    <HelpModal open={modal === 'help'} onClose={() => setModal(null)} />
    </>
  )
}