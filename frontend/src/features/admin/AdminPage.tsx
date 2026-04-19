import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@shared/api/client'
import { useAuth } from '@shared/auth/AuthProvider'
import { DashboardsTab } from './tabs/DashboardsTab'
import {
  LayoutDashboard, Users, Shield, ScrollText, Calendar, Target,
  ChevronLeft, Package, Layers,
} from 'lucide-react'

// ============================================================================
// AdminPage — Trang quản trị hệ thống
//
// Sidebar tổ chức tab thành 2 nhóm:
//   1. Tab chung (mọi admin đều thấy): Dashboard, Người dùng, Phân quyền, Nhật ký
//   2. Tab nghiệp vụ (theo nhóm tab_groups): Kỳ báo cáo, KPI, Nguyên liệu...
//
// Quyền hạn admin load từ GET /api/admin/me:
//   - Super admin: thấy tất cả tabs + nội dung không giới hạn
//   - Admin bộ phận: chỉ thấy tabs được gán + nội dung trong scope
// ============================================================================

/** Cấu hình tab tĩnh — 4 tab chung */
const BASE_TABS: TabDef[] = [
  { id: 'dashboards',  icon: LayoutDashboard, label: 'Dashboard' },
  { id: 'users',       icon: Users,           label: 'Người dùng' },
  { id: 'permissions', icon: Shield,           label: 'Phân quyền' },
  { id: 'log',         icon: ScrollText,       label: 'Nhật ký' },
]

/** Tab nghiệp vụ — map tab_id → icon + label mặc định */
const EXTRA_TAB_DEFS: Record<string, { icon: typeof Calendar; label: string }> = {
  kbc:       { icon: Calendar, label: 'Kỳ báo cáo' },
  kpi:       { icon: Target,   label: 'KPI' },
  inventory: { icon: Package,  label: 'Nguyên liệu' },
}

interface TabDef {
  id: string
  icon: typeof LayoutDashboard
  label: string
  group?: string    // Tên nhóm nghiệp vụ (chỉ tab mở rộng có)
}

interface AdminScope {
  scope_type: string
  scope_value: string
  tab_group_id: number | null
  group_name: string | null
  group_tabs: string | null
  can_create: boolean
  can_edit: boolean
  can_delete: boolean
}

interface AdminPerms {
  admin_level: string
  is_super: boolean
  scopes: AdminScope[]
  allowed_tabs: string[]
}

export default function AdminPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('dashboards')
  const [perms, setPerms] = useState<AdminPerms | null>(null)
  const [loading, setLoading] = useState(true)
  const [tabGroups, setTabGroups] = useState<{ id: number; name: string; tabs: string }[]>([])

  // Load phân quyền admin
  useEffect(() => {
    async function load() {
      try {
        const res = await apiClient.get<{ success: boolean } & AdminPerms>('/api/admin/me')
        if (res.success) {
          setPerms({
            admin_level: res.admin_level,
            is_super: res.is_super,
            scopes: res.scopes,
            allowed_tabs: res.allowed_tabs,
          })
        }
      } catch (e) {
        console.warn('Không tải được phân quyền admin, dùng quyền mặc định:', e)
        // Fallback: hiện 4 tab chung
        setPerms({
          admin_level: 'department',
          is_super: false,
          scopes: [],
          allowed_tabs: ['dashboards', 'users', 'permissions', 'log'],
        })
      }

      // Load tab groups
      try {
        const gRes = await apiClient.get<{ success: boolean; data: typeof tabGroups }>('/api/admin/tab-groups')
        if (gRes.success) setTabGroups(gRes.data)
      } catch { /* bỏ qua */ }

      setLoading(false)
    }
    load()
  }, [])

  // Xây dựng danh sách tab hiển thị
  const { baseTabs, groupedTabs } = buildTabs(perms, tabGroups)

  // Kiểm tra tab hiện tại có quyền không
  const allTabIds = [...baseTabs.map(t => t.id), ...groupedTabs.flatMap(g => g.tabs.map(t => t.id))]
  if (!allTabIds.includes(activeTab) && allTabIds.length > 0) {
    // Tab hiện tại không có quyền → chuyển về tab đầu tiên
    if (activeTab !== allTabIds[0]) setActiveTab(allTabIds[0])
  }

  // Lấy scope hiện tại cho tab đang active
  const currentScope = perms?.scopes.find(s => {
    if (s.tab_group_id === null) return true // scope chung
    // tìm group chứa tab đang active
    const group = tabGroups.find(g => g.id === s.tab_group_id)
    if (!group) return false
    return group.tabs.split(',').map(t => t.trim()).includes(activeTab)
  })

  return (
    <div className="adm">
      {/* Sidebar */}
      <div className="adm-sidebar">
        <div className="adm-sidebar-head">
          <button className="adm-back" onClick={() => navigate('/dashboards')}>
            <ChevronLeft className="h-4 w-4" /> Về trang chủ
          </button>
          <div className="adm-sidebar-title">Quản trị</div>
          <div className="adm-sidebar-user">{user?.displayName}</div>
          {perms && (
            <div className="adm-sidebar-level">
              {perms.is_super ? 'Quản trị viên cấp cao' : 'Quản trị bộ phận'}
            </div>
          )}
        </div>

        <nav className="adm-nav">
          {/* 4 tab chung */}
          <div className="adm-nav-group-label">Chung</div>
          {baseTabs.map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              className={`adm-nav-item ${activeTab === id ? 'active' : ''}`}
              onClick={() => setActiveTab(id)}
            >
              <Icon className="h-4 w-4" /><span>{label}</span>
            </button>
          ))}

          {/* Tab nghiệp vụ theo nhóm */}
          {groupedTabs.map((group) => (
            <div key={group.name}>
              <div className="adm-nav-group-label">{group.name}</div>
              {group.tabs.map(({ id, icon: Icon, label }) => (
                <button
                  key={id}
                  className={`adm-nav-item ${activeTab === id ? 'active' : ''}`}
                  onClick={() => setActiveTab(id)}
                >
                  <Icon className="h-4 w-4" /><span>{label}</span>
                </button>
              ))}
            </div>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="adm-content">
        <div className="adm-content-head">
          <h2 className="adm-content-title">
            {[...baseTabs, ...groupedTabs.flatMap(g => g.tabs)].find(t => t.id === activeTab)?.label || activeTab}
          </h2>
          {perms && !perms.is_super && currentScope?.scope_value && (
            <span className="adm-scope-badge">
              <Layers className="h-3 w-3" /> Phạm vi: {currentScope.scope_value}
            </span>
          )}
        </div>
        <div className="adm-content-body">
          {loading ? (
            <div className="adm-placeholder">Đang tải...</div>
          ) : (
            <>
              {activeTab === 'dashboards' && <DashboardsTab />}
              {activeTab === 'users' && <PlaceholderTab name="Người dùng" />}
              {activeTab === 'permissions' && <PlaceholderTab name="Phân quyền" />}
              {activeTab === 'log' && <PlaceholderTab name="Nhật ký" />}
              {activeTab === 'kbc' && <PlaceholderTab name="Kỳ báo cáo" />}
              {activeTab === 'kpi' && <PlaceholderTab name="KPI" />}
              {activeTab === 'inventory' && <PlaceholderTab name="Nguyên liệu" />}
            </>
          )}
        </div>
      </div>
    </div>
  )
}


// ═══ Helpers ═══

function buildTabs(perms: AdminPerms | null, tabGroups: { id: number; name: string; tabs: string }[]) {
  const allowed = new Set(perms?.allowed_tabs || ['dashboards', 'users', 'permissions', 'log'])

  // 4 tab chung — luôn hiện nhưng filter theo allowed
  const baseTabs = BASE_TABS.filter(t => allowed.has(t.id))

  // Tab nghiệp vụ — nhóm theo tab_group
  const groupedTabs: { name: string; tabs: TabDef[] }[] = []

  for (const group of tabGroups) {
    const tabs: TabDef[] = []
    for (const tabId of group.tabs.split(',').map(t => t.trim())) {
      if (!allowed.has(tabId)) continue
      const def = EXTRA_TAB_DEFS[tabId]
      if (def) {
        tabs.push({ id: tabId, icon: def.icon, label: def.label, group: group.name })
      } else {
        // Tab chưa có trong EXTRA_TAB_DEFS → dùng icon mặc định
        tabs.push({ id: tabId, icon: Layers, label: tabId, group: group.name })
      }
    }
    if (tabs.length > 0) {
      groupedTabs.push({ name: group.name, tabs })
    }
  }

  return { baseTabs, groupedTabs }
}

function PlaceholderTab({ name }: { name: string }) {
  return (
    <div className="adm-placeholder">
      <p>Tab "{name}" — đang phát triển</p>
      <p className="adm-placeholder-hint">Chức năng này sẽ được chuyển từ trang quản trị cũ sang</p>
    </div>
  )
}