import { create } from 'zustand'

interface LayoutState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void

  // Active bottom sheet (mobile)
  activeSheet: string | null
  openSheet: (type: string) => void
  closeSheet: () => void
}

export const useLayoutStore = create<LayoutState>((set) => ({
  sidebarOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  activeSheet: null,
  openSheet: (type) => set({ activeSheet: type }),
  closeSheet: () => set({ activeSheet: null }),
}))
