import { create } from 'zustand'
import type { MergedKBC } from '@shared/ui/slicers/kbc-picker.types'

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

  // Selected KBC (merged result — persists across pages)
  currentKBC: MergedKBC | null
  setCurrentKBC: (kbc: MergedKBC | null) => void

  // Selected KBC IDs (for multi-select state)
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

  currentKBC: null,
  setCurrentKBC: (kbc) => set({ currentKBC: kbc }),

  selectedKbcIds: new Set(),
  setSelectedKbcIds: (ids) => set({ selectedKbcIds: ids }),

  resetFilters: () =>
    set({
      selectedBP: '',
      selectedNV: null,
      selectedKH: null,
      dateA: '',
      dateB: '',
      currentKBC: null,
      selectedKbcIds: new Set(),
    }),
}))