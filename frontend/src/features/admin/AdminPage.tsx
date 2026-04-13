import { useState } from 'react'

const TABS = [
  { id: 'users', label: 'Người dùng' },
  { id: 'dashboards', label: 'Dashboard' },
  { id: 'permissions', label: 'Phân quyền' },
  { id: 'kbc', label: 'Kỳ báo cáo' },
  { id: 'kpi', label: 'KPI' },
  { id: 'log', label: 'Log' },
] as const

type TabId = (typeof TABS)[number]['id']

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<TabId>('users')

  return (
    <div className="flex h-dvh flex-col">
      {/* Top bar */}
      <header className="flex h-12 shrink-0 items-center justify-between bg-surface-7 px-4 text-white">
        <span className="text-sm font-extrabold">Quản trị hệ thống</span>
        <div className="flex items-center gap-2 text-xs">
          <a href="/dashboards" className="rounded-md border border-white/15 bg-white/10 px-3 py-1 text-[11px] hover:bg-white/20">
            Dashboard
          </a>
          <a href="/logout" className="rounded-md border border-white/15 bg-white/10 px-3 py-1 text-[11px] hover:bg-white/20">
            Đăng xuất
          </a>
        </div>
      </header>

      {/* Tab bar */}
      <div className="flex shrink-0 gap-0 border-b-2 border-surface-2 bg-white px-4">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative px-5 py-3 text-[13px] font-bold transition-colors ${
              activeTab === tab.id
                ? 'text-brand-600 after:absolute after:inset-x-0 after:bottom-[-2px] after:h-[2.5px] after:rounded-t after:bg-brand-600'
                : 'text-surface-4 hover:text-surface-6'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'users' && <UsersTabPlaceholder />}
        {activeTab === 'dashboards' && <PlaceholderTab name="Dashboard" />}
        {activeTab === 'permissions' && <PlaceholderTab name="Phân quyền" />}
        {activeTab === 'kbc' && <PlaceholderTab name="Kỳ báo cáo" />}
        {activeTab === 'kpi' && <PlaceholderTab name="KPI" />}
        {activeTab === 'log' && <PlaceholderTab name="Audit Log" />}
      </div>
    </div>
  )
}

function UsersTabPlaceholder() {
  return (
    <div className="mx-auto max-w-[1400px]">
      <div className="mb-3 flex items-center gap-3">
        <div className="flex flex-1 items-center gap-2 rounded-lg border-[1.5px] border-surface-2 bg-white px-3 py-2">
          <input type="text" placeholder="Tìm tên, username, mã NVKD…" className="flex-1 text-sm outline-none" />
        </div>
        <button className="rounded-md bg-brand-600 px-4 py-2 text-xs font-bold text-white">+ Thêm</button>
      </div>
      <div className="rounded-lg border border-surface-2 bg-white p-8 text-center text-sm text-surface-4">
        TODO: Migrate user table from admin/_tab_users.html
      </div>
    </div>
  )
}

function PlaceholderTab({ name }: { name: string }) {
  return (
    <div className="flex h-64 items-center justify-center text-surface-4">
      <p>TODO: Migrate tab "{name}"</p>
    </div>
  )
}
