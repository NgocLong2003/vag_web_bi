/**
 * All API endpoint URLs in one place.
 * When backend changes a URL, fix it here only.
 */
export const ENDPOINTS = {
  // Auth
  auth: {
    login: '/login',
    logout: '/logout',
    settings: '/settings',
  },

  // Dashboard
  dashboard: {
    list: '/dashboards',
    reportUrl: '/api/report-url',
    dataStatus: '/api/data-status',
  },

  // Admin
  admin: {
    index: '/admin',
    userAdd: '/admin/user/add',
    userEdit: (id: number) => `/admin/user/${id}/edit`,
    userDelete: (id: number) => `/admin/user/${id}/delete`,
    userBp: (id: number) => `/admin/user/${id}/bp`,
    userPermissions: (id: number) => `/admin/user/${id}/permissions`,
    dashboardAdd: '/admin/dashboard/add',
    dashboardEdit: (id: number) => `/admin/dashboard/${id}/edit`,
    dashboardDelete: (id: number) => `/admin/dashboard/${id}/delete`,
    permToggle: '/admin/phan-quyen/toggle',
    permBulk: '/admin/phan-quyen/bulk',
    kbcAdd: '/admin/kbc/add',
    kbcEdit: (id: number) => `/admin/kbc/${id}/edit`,
    kbcDelete: (id: number) => `/admin/kbc/${id}/delete`,
    kpiData: '/admin/kpi/data',
    kpiSaveCell: '/admin/kpi/save-cell',
    kpiReassign: '/admin/kpi/reassign',
    kpiExport: '/admin/kpi/export',
    kpiImportExcel: '/admin/kpi/import-excel',
    auditLog: '/admin/audit-log',
    bulkCreateUsers: '/admin/bulk-create-users',
  },

  // Analytics
  analytics: {
    summary: '/api/analytics/summary',
  },

  // Reports — each report has its own API prefix
  reports: {
    kinhDoanh: {
      base: '/reports/bao-cao-kinh-doanh',
      hierarchy: '/reports/bao-cao-kinh-doanh/api/hierarchy',
      khachhang: '/reports/bao-cao-kinh-doanh/api/khachhang',
      kyBaoCao: '/reports/bao-cao-kinh-doanh/api/ky-bao-cao',
      congno: '/reports/bao-cao-kinh-doanh/api/congno',
      doanhso: '/reports/bao-cao-kinh-doanh/api/doanhso',
      doanhthu: '/reports/bao-cao-kinh-doanh/api/doanhthu',
      exportExcel: '/reports/bao-cao-kinh-doanh/api/export_excel',
    },
    khachHang: {
      base: '/reports/bao-cao-khach-hang',
      hierarchy: '/reports/bao-cao-khach-hang/api/hierarchy',
      khachhang: '/reports/bao-cao-khach-hang/api/khachhang',
      kyBaoCao: '/reports/bao-cao-khach-hang/api/ky-bao-cao',
      congno: '/reports/bao-cao-khach-hang/api/congno',
      doanhso: '/reports/bao-cao-khach-hang/api/doanhso',
      doanhthu: '/reports/bao-cao-khach-hang/api/doanhthu',
      dunotrongky: '/reports/bao-cao-khach-hang/api/dunotrongky',
      dunocuoiky: '/reports/bao-cao-khach-hang/api/dunocuoiky',
      doanhsoChitiet: '/reports/bao-cao-khach-hang/api/doanhso_chitiet',
      doanhthuChitiet: '/reports/bao-cao-khach-hang/api/doanhthu_chitiet',
      thuongChitiet: '/reports/bao-cao-khach-hang/api/thuong_chitiet',
      tralaiChitiet: '/reports/bao-cao-khach-hang/api/tralai_chitiet',
      exportExcel: '/reports/bao-cao-khach-hang/api/export_excel',
    },
    chiTiet: {
      base: '/reports/bao-cao-chi-tiet',
      hierarchy: '/reports/bao-cao-chi-tiet/api/hierarchy',
      khachhang: '/reports/bao-cao-chi-tiet/api/khachhang',
      doanhsoChitiet: '/reports/bao-cao-chi-tiet/api/doanhso_chitiet',
      doanhthuChitiet: '/reports/bao-cao-chi-tiet/api/doanhthu_chitiet',
      exportExcel: '/reports/bao-cao-chi-tiet/api/export_excel',
    },
    banRa: {
      base: '/reports/bao-cao-ban-ra',
      data: '/reports/bao-cao-ban-ra/api/data',
      exportExcel: '/reports/bao-cao-ban-ra/api/export_excel',
    },
    kpi: {
      base: '/reports/bao-cao-kpi',
      kbc: '/reports/bao-cao-kpi/api/kbc',
      data: '/reports/bao-cao-kpi/api/data',
      detail: '/reports/bao-cao-kpi/api/detail',
    },
    nguyenLieu: {
      base: '/reports/bao-cao-nguyen-lieu',
      data: '/reports/bao-cao-nguyen-lieu/api/data',
      vattu: '/reports/bao-cao-nguyen-lieu/api/vattu',
      sanpham: '/reports/bao-cao-nguyen-lieu/api/sanpham',
      exportXuat: '/reports/bao-cao-nguyen-lieu/api/export-xuat',
    },
  },
} as const