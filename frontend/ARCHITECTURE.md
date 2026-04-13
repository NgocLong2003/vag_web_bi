# VietAnh BI — Frontend Architecture (React + TypeScript)

## 1. Tổng quan

### Stack
- **Framework:** React 18 + TypeScript
- **Build:** Vite
- **Styling:** Tailwind CSS + CSS Modules (cho component-specific styles)
- **State:** Zustand (global) + React Query (server state/cache)
- **Routing:** React Router v7
- **Charts:** Recharts (declarative) + D3 (custom SVG canvas như KPI graph)
- **Table:** TanStack Table v8
- **Icons:** Lucide React
- **Export:** SheetJS (xlsx) — client-side, hoặc gọi API backend
- **Mobile:** Responsive-first, bottom dock pattern

### Kiến trúc tổng thể

```
Flask API (backend, giữ nguyên)
    ↕ JSON REST API
React SPA (frontend, mới)
    ├── Desktop: Header + Sidebar + Content
    └── Mobile: Content + Bottom Dock
```

### Data Flow

```
Data Sources → Flask API → React Query Cache → Zustand Store → React Components
                                                    ↓
                                              Permission Filter
                                                    ↓
                                              Rendered UI
```

---

## 2. Folder Structure

```
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
│
├── public/
│   └── favicon.svg
│
└── src/
    ├── main.tsx                          # Entry point
    ├── App.tsx                           # Root: Router + Providers
    ├── routes.tsx                        # Route definitions
    │
    ├── config/
    │   ├── api.ts                        # API base URL, axios/fetch config
    │   ├── constants.ts                  # App-wide constants
    │   └── env.ts                        # Environment variables
    │
    ├── types/                            # Global TypeScript types
    │   ├── api.ts                        # API response shapes
    │   ├── auth.ts                       # User, Session, Role
    │   ├── report.ts                     # Report, Column, KBC, Hierarchy
    │   ├── admin.ts                      # Dashboard, User management
    │   └── datasource.ts                 # DataSource types
    │
    ├── shared/                           # ★ SHARED: dùng across tất cả features
    │   │
    │   ├── api/                          # API client layer
    │   │   ├── client.ts                 # Fetch wrapper (auth headers, error handling)
    │   │   ├── endpoints.ts              # All API endpoint URLs
    │   │   └── hooks/                    # React Query hooks dùng chung
    │   │       ├── useHierarchy.ts       # GET /api/hierarchy
    │   │       ├── useKhachHang.ts       # GET /api/khachhang
    │   │       ├── useKyBaoCao.ts        # GET /api/ky-bao-cao
    │   │       └── useExport.ts          # POST export Excel
    │   │
    │   ├── auth/                         # Auth & permission logic
    │   │   ├── AuthProvider.tsx          # Context: current user, token
    │   │   ├── useAuth.ts               # Hook: login, logout, session
    │   │   ├── usePermissions.ts        # Hook: RLS, BP-scoped, allowed NV
    │   │   ├── ProtectedRoute.tsx       # Route guard (login required)
    │   │   └── AdminRoute.tsx           # Route guard (admin required)
    │   │
    │   ├── stores/                       # Zustand global stores
    │   │   ├── useFilterStore.ts         # Selected BP, NV, KH, date range
    │   │   ├── useLayoutStore.ts         # Sidebar open, mobile dock, theme
    │   │   └── useReportStore.ts         # Active report state, columns
    │   │
    │   ├── hooks/                        # Custom hooks dùng chung
    │   │   ├── useResponsive.ts          # isMobile, isLandscape, breakpoint
    │   │   ├── useHybridScroll.ts        # Mobile address bar hiding
    │   │   ├── useColumnResize.ts        # Drag to resize table columns
    │   │   ├── useTreeExpand.ts          # Expand/collapse tree state
    │   │   ├── useDebounce.ts
    │   │   └── useLocalStorage.ts
    │   │
    │   ├── ui/                           # ★ GENERIC UI COMPONENTS (BI building blocks)
    │   │   │
    │   │   ├── layout/                   # App-level layout
    │   │   │   ├── AppShell.tsx          # Desktop: Header + Sidebar + Content
    │   │   │   ├── Header.tsx            # Top bar (desktop)
    │   │   │   ├── Sidebar.tsx           # Left nav (desktop, slide-in mobile)
    │   │   │   ├── BottomDock.tsx        # Mobile bottom navigation
    │   │   │   ├── BottomSheet.tsx       # Mobile modal from bottom
    │   │   │   └── ReportLayout.tsx      # Report-specific: toolbar + table + footer
    │   │   │
    │   │   ├── data-display/             # BI display components
    │   │   │   ├── DataTable/
    │   │   │   │   ├── DataTable.tsx     # TanStack Table wrapper
    │   │   │   │   ├── DataTable.types.ts
    │   │   │   │   ├── TableHeader.tsx   # Sticky header, sort, filter
    │   │   │   │   ├── TableBody.tsx     # Virtual scrolling body
    │   │   │   │   ├── TableFooter.tsx   # Sticky footer with totals
    │   │   │   │   └── ColumnFilter.tsx  # Per-column filter dropdown
    │   │   │   │
    │   │   │   ├── TreeTable/
    │   │   │   │   ├── TreeTable.tsx     # Hierarchical table (NV → KH rows)
    │   │   │   │   ├── TreeTable.types.ts
    │   │   │   │   ├── TreeRow.tsx       # NV row with expand/collapse
    │   │   │   │   ├── LeafRow.tsx       # KH row (clickable for drill-down)
    │   │   │   │   └── TreeLines.tsx     # Visual tree connector lines
    │   │   │   │
    │   │   │   ├── KPICard.tsx           # Single metric display
    │   │   │   ├── ChartWrapper.tsx      # Recharts wrapper with responsive
    │   │   │   ├── NumberCell.tsx        # Formatted number (pos/neg/zero)
    │   │   │   ├── Sparkline.tsx         # Inline mini chart
    │   │   │   └── EmptyState.tsx        # No data placeholder
    │   │   │
    │   │   ├── filters/                  # BI filter components
    │   │   │   ├── Slicer.tsx            # Generic slicer (dropdown/checkbox/radio)
    │   │   │   ├── DateRangePicker.tsx   # Date range with presets
    │   │   │   ├── TreePicker/
    │   │   │   │   ├── TreePicker.tsx    # NV picker (checkbox tree, search)
    │   │   │   │   └── TreePicker.types.ts
    │   │   │   ├── KBCPicker/
    │   │   │   │   ├── KBCPicker.tsx     # Kỳ báo cáo picker (multi-select tree)
    │   │   │   │   └── KBCPicker.types.ts
    │   │   │   ├── SearchSelect.tsx      # Autocomplete search (KH search)
    │   │   │   └── BPSelector.tsx        # Bộ phận pills/dropdown
    │   │   │
    │   │   ├── navigation/
    │   │   │   ├── PageNavigator.tsx     # Tab-like page navigation
    │   │   │   └── Breadcrumb.tsx
    │   │   │
    │   │   ├── feedback/                 # User feedback
    │   │   │   ├── Toast.tsx             # Toast notifications
    │   │   │   ├── LoadingOverlay.tsx    # Full-screen loading
    │   │   │   ├── Skeleton.tsx          # Shimmer placeholder
    │   │   │   └── StatusChip.tsx        # Data freshness indicator
    │   │   │
    │   │   ├── actions/                  # Action components
    │   │   │   ├── ExportButton.tsx      # Export Excel/PDF
    │   │   │   ├── ToolbarButton.tsx     # Standard toolbar button
    │   │   │   └── RefreshButton.tsx     # Reload data
    │   │   │
    │   │   └── overlays/                 # Modal & overlay
    │   │       ├── Modal.tsx             # Desktop modal
    │   │       ├── DrilldownModal.tsx    # Detail popup (lịch sử KH)
    │   │       └── ConfirmDialog.tsx
    │   │
    │   └── utils/                        # Pure utility functions
    │       ├── format.ts                 # fmtNumber, fmtDate, fmtPercent
    │       ├── tree.ts                   # buildTree, walkTree, getDescendants
    │       ├── permission.ts             # computeAllowedNV, filterByBP
    │       ├── aggregate.ts              # Roll-up totals in tree
    │       ├── export.ts                 # Build Excel payload
    │       └── cn.ts                     # classNames utility
    │
    ├── features/                         # ★ FEATURE MODULES
    │   │
    │   ├── auth/                         # Login/Logout/Settings
    │   │   ├── LoginPage.tsx
    │   │   ├── SettingsPage.tsx
    │   │   └── api.ts                    # login(), logout() API calls
    │   │
    │   ├── dashboard/                    # Dashboard list + Power BI embed
    │   │   ├── DashboardListPage.tsx
    │   │   ├── DashboardViewPage.tsx     # Power BI iframe embed
    │   │   ├── DashboardCard.tsx
    │   │   └── api.ts
    │   │
    │   ├── admin/                        # Admin panel
    │   │   ├── AdminPage.tsx             # Tab container
    │   │   ├── tabs/
    │   │   │   ├── UsersTab/
    │   │   │   │   ├── UsersTab.tsx
    │   │   │   │   ├── UserTable.tsx
    │   │   │   │   ├── UserFormModal.tsx
    │   │   │   │   └── BulkCreateButton.tsx
    │   │   │   ├── DashboardsTab/
    │   │   │   │   ├── DashboardsTab.tsx
    │   │   │   │   └── DashboardFormModal.tsx
    │   │   │   ├── PermissionsTab/
    │   │   │   │   ├── PermissionsTab.tsx
    │   │   │   │   └── PermissionMatrix.tsx  # Checkbox grid
    │   │   │   ├── KBCTab/
    │   │   │   │   ├── KBCTab.tsx
    │   │   │   │   └── KBCFormModal.tsx
    │   │   │   ├── KPITab/
    │   │   │   │   ├── KPITab.tsx
    │   │   │   │   ├── KPIGraph.tsx      # SVG canvas (drag, wire, edit)
    │   │   │   │   ├── KPITable.tsx      # Editable tree table
    │   │   │   │   └── UnassignedPanel.tsx
    │   │   │   └── AuditLogTab/
    │   │   │       └── AuditLogTab.tsx
    │   │   └── api.ts                    # Admin API calls
    │   │
    │   ├── analytics/                    # Usage analytics
    │   │   ├── AnalyticsPage.tsx
    │   │   └── api.ts
    │   │
    │   └── reports/                      # ★ TẤT CẢ BÁO CÁO
    │       │
    │       ├── _shared/                  # Shared across all reports
    │       │   ├── ReportShell.tsx        # Standard report wrapper
    │       │   │                          #   Desktop: Toolbar + TreeTable + Footer
    │       │   │                          #   Mobile: Content + BottomDock
    │       │   ├── ReportToolbar.tsx      # Desktop toolbar (date, BP, NV, export)
    │       │   ├── ReportMobileDock.tsx   # Mobile bottom dock buttons
    │       │   ├── ReportMobileSheets.tsx # Mobile bottom sheets (filter, actions)
    │       │   ├── useReportData.ts       # Hook: load hierarchy + KH + data
    │       │   ├── useReportTree.ts       # Hook: build tree, aggregate, expand
    │       │   ├── useReportExport.ts     # Hook: export Excel
    │       │   └── report.types.ts        # Shared report types
    │       │
    │       ├── kinh-doanh/               # Báo cáo Kinh Doanh
    │       │   ├── KinhDoanhPage.tsx      # Page component
    │       │   ├── KinhDoanhColumns.tsx   # Dynamic columns (add/remove/reorder)
    │       │   ├── KinhDoanhConfig.ts     # Column definitions, API endpoints
    │       │   └── api.ts                # congno, doanhso, doanhthu APIs
    │       │
    │       ├── khach-hang/               # Báo cáo Khách Hàng
    │       │   ├── KhachHangPage.tsx
    │       │   ├── KhachHangColumns.ts
    │       │   ├── HistoryModal.tsx       # Drill-down lịch sử KH
    │       │   └── api.ts
    │       │
    │       ├── chi-tiet/                 # Báo cáo Chi Tiết
    │       │   ├── ChiTietPage.tsx
    │       │   ├── ChiTietConfig.ts
    │       │   └── api.ts
    │       │
    │       ├── ban-ra/                   # Báo cáo Bán Ra (flat table)
    │       │   ├── BanRaPage.tsx
    │       │   ├── BanRaFilters.tsx
    │       │   ├── BanRaConfig.ts
    │       │   └── api.ts
    │       │
    │       ├── kpi/                      # Báo cáo KPI (graph + table)
    │       │   ├── KPIReportPage.tsx
    │       │   ├── KPICanvas.tsx          # SVG interactive graph
    │       │   ├── KPIDetailPanel.tsx
    │       │   └── api.ts
    │       │
    │       └── san-xuat/                 # Báo cáo Sản Xuất
    │           ├── nguyen-lieu/
    │           │   ├── NguyenLieuPage.tsx
    │           │   ├── PivotTable.tsx     # 12-month pivot
    │           │   ├── SanPhamSection.tsx
    │           │   └── api.ts
    │           └── (future reports...)
    │
    └── styles/
        ├── globals.css                   # Tailwind directives + CSS variables
        ├── tokens.css                    # Design tokens (colors, spacing, fonts)
        └── animations.css               # Shared keyframes
```

---

## 3. Key Design Decisions

### 3.1 Why Feature-Based (not Layer-Based)

```
❌ Layer-based (khó scale):        ✅ Feature-based (scale tốt):
components/                         features/
  Chart.tsx                           kinh-doanh/
  Table.tsx                             Page.tsx
  Slicer.tsx                            Columns.tsx
pages/                                  api.ts
  KinhDoanh.tsx                       khach-hang/
  KhachHang.tsx                         Page.tsx
api/                                    HistoryModal.tsx
  kinhdoanh.ts                          api.ts
  khachhang.ts
```

Feature-based: mở 1 folder = thấy hết mọi thứ liên quan.
Thêm report mới = thêm 1 folder, không sửa gì ở shared.

### 3.2 State Management

```
Zustand (shared/stores/)     → App-wide state: auth, layout, active filters
React Query (shared/api/)    → Server data: hierarchy, KH, report data
Local useState               → Component-only: modal open, input value
```

Không dùng Redux — quá nặng cho use case này. Zustand đủ mạnh, đơn giản, TypeScript-first.

### 3.3 Permission Model (3 tầng)

```typescript
// types/auth.ts
interface User {
  id: number
  username: string
  displayName: string
  role: 'admin' | 'user'
  maNvkdList: string[]      // RLS: chỉ thấy data của NV này + cấp dưới
  maBp: string[]             // BP-scoped: admin chỉ quản lý user thuộc BP này
  dashboardIds: number[]     // Report-level: user được xem report nào
}
```

- **Report Access:** `user.dashboardIds` → route guard
- **Row-Level Security:** `user.maNvkdList` → filter hierarchy tree
- **Admin Scope:** `user.maBp` → filter user list in admin panel

### 3.4 Data Source Abstraction

```typescript
// shared/api/client.ts
// Frontend không cần biết backend dùng DuckDB hay SQL Server
// Chỉ cần gọi đúng API endpoint, backend tự route tới datasource phù hợp

// Mỗi report define API calls riêng:
// features/reports/kinh-doanh/api.ts
export const fetchCongNo = (params: CongNoParams) =>
  apiClient.post<CongNoResponse>('/reports/bao-cao-kinh-doanh/api/congno', params)
```

### 3.5 Responsive Strategy

```
Desktop (>768px):
  ┌─────────────────────────────────────┐
  │ Header (logo, nav, user, actions)   │
  ├────────┬────────────────────────────┤
  │Sidebar │ Report Content             │
  │(nav)   │ ┌─Toolbar──────────────┐   │
  │        │ │ BP | NV | Date | ... │   │
  │        │ ├───────────────────────┤   │
  │        │ │ TreeTable / Chart     │   │
  │        │ ├───────────────────────┤   │
  │        │ │ Footer (totals)       │   │
  │        │ └───────────────────────┘   │
  └────────┴────────────────────────────┘

Mobile (<768px):
  ┌─────────────────────┐
  │ Report Content      │
  │ (full width)        │
  │ ┌─────────────────┐ │
  │ │ TreeTable       │ │
  │ │ (sticky col 1)  │ │
  │ │                 │ │
  │ └─────────────────┘ │
  ├─────────────────────┤
  │ ☰  🔍  📊  🔎  ⋮  │ ← Bottom Dock
  └─────────────────────┘
```

---

## 4. Thêm Report Mới — Checklist

```
1. Tạo folder: features/reports/ten-report/
2. Tạo files:
   - TenReportPage.tsx      ← Page component (compose ReportShell + custom)
   - TenReportConfig.ts     ← Column defs, API endpoints
   - api.ts                 ← API calls specific to this report
3. Thêm route: routes.tsx
4. Thêm vào report registry: features/reports/index.ts
5. Backend: thêm Blueprint + API endpoints (nếu chưa có)
6. Admin: tạo dashboard entry với type='report', slug khớp
```

Không cần sửa gì ở shared/, không cần sửa component nào khác.

---

## 5. Migration Path

```
Phase 1 (Ngày 1): Setup + Core
  ✓ Vite + React + TS + Tailwind
  ✓ Folder structure
  ✓ Auth flow (login, session, route guards)
  ✓ AppShell (Header, Sidebar, BottomDock)
  ✓ API client + React Query setup
  ✓ Permission hooks

Phase 2 (Ngày 2): 1 Report làm mẫu
  ✓ Shared report components (ReportShell, TreeTable, NumberCell)
  ✓ Shared filters (TreePicker, KBCPicker, BPSelector, DateRange)
  ✓ Migrate "Báo cáo Kinh Doanh" hoặc "Báo cáo Bán Ra" (đơn giản hơn)
  ✓ Export Excel
  ✓ Mobile responsive

Phase 3 (Dần dần): Migrate từng report
  - Mỗi report mới follow pattern từ Phase 2
  - Flask giữ nguyên API, bỏ dần Jinja templates
  - Dashboard list + Power BI embed
  - Admin panel

Phase 4 (Khi ổn định): Config-driven
  - Report registry tự động
  - Column config → auto render
  - Tiến tới report builder (tương lai xa)
```
