import { create } from 'zustand'

interface FilterState {
  // Selected BP (empty = all)
  selectedBP: string
  setSelectedBP: (bp: string) => void

  // Selected NV set (null = all allowed)
  selectedNV: Set<string> | null
  setSelectedNV: (nv: Set<string> | null) => void

  // Selected KH
  selectedKH: { ma_kh: string; ten_kh: string } | null
  setSelectedKH: (kh: { ma_kh: string; ten_kh: string } | null) => void

  // Date range
  dateA: string
  dateB: string
  setDateRange: (a: string, b: string) => void

  // Selected KBC IDs
  selectedKbcIds: Set<number>
  setSelectedKbcIds: (ids: Set<number>) => void

  // Reset all filters
  resetFilters: () => void
}

export const useFilterStore = create<FilterState>((set) => ({
  selectedBP: '',
  setSelectedBP: (bp) => set({ selectedBP: bp }),

  selectedNV: null,
  setSelectedNV: (nv) => set({ selectedNV: nv }),

  selectedKH: null,
  setSelectedKH: (kh) => set({ selectedKH: kh }),

  dateA: '',
  dateB: '',
  setDateRange: (a, b) => set({ dateA: a, dateB: b }),

  selectedKbcIds: new Set(),
  setSelectedKbcIds: (ids) => set({ selectedKbcIds: ids }),

  resetFilters: () =>
    set({
      selectedBP: '',
      selectedNV: null,
      selectedKH: null,
      dateA: '',
      dateB: '',
      selectedKbcIds: new Set(),
    }),
}))
