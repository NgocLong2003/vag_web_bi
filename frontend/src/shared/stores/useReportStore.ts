import { create } from 'zustand'

// ============================================================================
// useReportStore — Kênh giao tiếp giữa trang báo cáo/dashboard và Header
//
// Page mount → set metadata (tên, update mode, download handler)
// Header đọc store → hiện tên đúng, badge đúng, gọi handler đúng
// Page unmount → clearReport()
// ============================================================================

interface ReportState {
  /** Tên báo cáo / dashboard hiện tại */
  reportName: string
  setReportName: (name: string) => void

  /** Chế độ cập nhật */
  updateMode: 'realtime' | 'scheduled'
  setUpdateMode: (mode: 'realtime' | 'scheduled') => void

  /** Tần suất cập nhật (cho scheduled: "30 phút/lần") */
  updateInterval: string
  setUpdateInterval: (text: string) => void

  /** Thời gian cập nhật gần nhất (cho scheduled: "5 phút trước") */
  lastUpdateText: string
  setLastUpdateText: (text: string) => void

  /** Handler tải xuống — page đăng ký, header gọi */
  downloadHandler: ((format: string) => void) | null
  setDownloadHandler: (handler: ((format: string) => void) | null) => void

  /** Đang tải xuống */
  downloading: boolean
  setDownloading: (v: boolean) => void

  /** Danh sách dashboard cho dropdown chuyển trang */
  dashboards: Array<{ id: string; name: string; slug: string; group: string; dashboard_type: string }>
  setDashboards: (list: ReportState['dashboards']) => void

  /** Reset khi rời trang */
  clearReport: () => void
}

export const useReportStore = create<ReportState>((set) => ({
  reportName: '',
  setReportName: (name) => set({ reportName: name }),

  updateMode: 'realtime',
  setUpdateMode: (mode) => set({ updateMode: mode }),

  updateInterval: '',
  setUpdateInterval: (text) => set({ updateInterval: text }),

  lastUpdateText: '',
  setLastUpdateText: (text) => set({ lastUpdateText: text }),

  downloadHandler: null,
  setDownloadHandler: (handler) => set({ downloadHandler: handler }),

  downloading: false,
  setDownloading: (v) => set({ downloading: v }),

  dashboards: [],
  setDashboards: (list) => set({ dashboards: list }),

  clearReport: () => set({
    reportName: '',
    updateMode: 'realtime',
    updateInterval: '',
    lastUpdateText: '',
    downloadHandler: null,
    downloading: false,
  }),
}))