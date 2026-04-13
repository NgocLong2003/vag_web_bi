import { Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@shared/auth/ProtectedRoute'
import { AdminRoute } from '@shared/auth/AdminRoute'
import { AppShell } from '@shared/ui/layout/AppShell'

// Lazy load pages
import { lazy, Suspense } from 'react'
import { LoadingOverlay } from '@shared/ui/feedback/LoadingOverlay'

const LoginPage = lazy(() => import('@features/auth/LoginPage'))
const SettingsPage = lazy(() => import('@features/auth/SettingsPage'))
const DashboardListPage = lazy(() => import('@features/dashboard/DashboardListPage'))
const DashboardViewPage = lazy(() => import('@features/dashboard/DashboardViewPage'))
const AdminPage = lazy(() => import('@features/admin/AdminPage'))
const AnalyticsPage = lazy(() => import('@features/analytics/AnalyticsPage'))

// Reports
const KinhDoanhPage = lazy(() => import('@features/reports/kinh-doanh/KinhDoanhPage'))
const KhachHangPage = lazy(() => import('@features/reports/khach-hang/KhachHangPage'))
const ChiTietPage = lazy(() => import('@features/reports/chi-tiet/ChiTietPage'))
const BanRaPage = lazy(() => import('@features/reports/ban-ra/BanRaPage'))
const KPIReportPage = lazy(() => import('@features/reports/kpi/KPIReportPage'))
const NguyenLieuPage = lazy(() => import('@features/reports/san-xuat/nguyen-lieu/NguyenLieuPage'))

function SuspenseWrap({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingOverlay visible message="Đang tải..." />}>{children}</Suspense>
}

export function AppRoutes() {
  return (
    <SuspenseWrap>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected — with AppShell */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            {/* Dashboard */}
            <Route path="/dashboards" element={<DashboardListPage />} />
            <Route path="/d/:slug" element={<DashboardViewPage />} />

            {/* Settings */}
            <Route path="/settings" element={<SettingsPage />} />

            {/* Reports (each report is a route under /d/:slug) */}
            {/* These are also accessible via /d/:slug when dashboard_type='report' */}
            <Route path="/r/bao-cao-kinh-doanh" element={<KinhDoanhPage />} />
            <Route path="/r/bao-cao-khach-hang" element={<KhachHangPage />} />
            <Route path="/r/bao-cao-chi-tiet" element={<ChiTietPage />} />
            <Route path="/r/bao-cao-ban-ra" element={<BanRaPage />} />
            <Route path="/r/bao-cao-kpi" element={<KPIReportPage />} />
            <Route path="/r/bao-cao-nguyen-lieu" element={<NguyenLieuPage />} />

            {/* Analytics */}
            <Route path="/r/analytics" element={<AnalyticsPage />} />
          </Route>

          {/* Admin — separate layout */}
          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<AdminPage />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="/" element={<Navigate to="/dashboards" replace />} />
        <Route path="*" element={<Navigate to="/dashboards" replace />} />
      </Routes>
    </SuspenseWrap>
  )
}
