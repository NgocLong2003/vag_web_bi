import type { NVNode } from '@/types'
import type { ColumnData, AggregatedValues } from '@/features/reports/shared/report.types'

/**
 * Aggregate column data into tree nodes.
 *
 * For each NV node:
 *   - Own KH values: from columnData[nvkd][kh]
 *   - Total: sum of own KH values + sum of children totals
 *
 * This is a bottom-up aggregation (deepest nodes first).
 *
 * @param hierarchy Flat array of hierarchy nodes (sorted by level desc for bottom-up)
 * @param nvMap Map of nvkd → NVNode
 * @param columnData Data for this column: nvkd → kh → value
 * @param selectedNV If not null, only include data for selected NVs (RLS)
 * @returns Map of nvkd → AggregatedValues
 */
export function aggregateColumn(
  hierarchy: { ma_nvkd: string; level: number }[],
  nvMap: Map<string, NVNode>,
  columnData: ColumnData,
  selectedNV: Set<string> | null,
): Map<string, AggregatedValues> {
  const result = new Map<string, AggregatedValues>()

  // Initialize all nodes
  nvMap.forEach((_, id) => {
    result.set(id, { kh: {}, total: null })
  })

  // Fill own KH values
  Object.entries(columnData).forEach(([nvkd, khValues]) => {
    const agg = result.get(nvkd)
    if (!agg) return
    Object.entries(khValues).forEach(([mk, v]) => {
      agg.kh[mk] = (agg.kh[mk] || 0) + v
    })
  })

  // Bottom-up roll-up: process deepest nodes first
  const sorted = [...hierarchy].sort((a, b) => b.level - a.level)

  sorted.forEach((h) => {
    const node = nvMap.get(h.ma_nvkd)
    const agg = result.get(h.ma_nvkd)
    if (!node || !agg) return

    const isSelected = selectedNV === null || selectedNV.has(h.ma_nvkd)

    let sum = 0
    let hasValue = false

    // Own KH values (only if selected)
    if (isSelected) {
      Object.values(agg.kh).forEach((v) => {
        sum += v
        hasValue = true
      })
    }

    // Children totals
    node.children.forEach((child) => {
      const childAgg = result.get(child.ma_nvkd)
      if (childAgg && childAgg.total != null) {
        sum += childAgg.total
        hasValue = true
      }
    })

    agg.total = hasValue ? sum : null
  })

  return result
}

/**
 * Get total for a specific NV + column from aggregated data.
 */
export function getNodeTotal(
  aggregated: Map<string, AggregatedValues>,
  nvkd: string,
): number | null {
  return aggregated.get(nvkd)?.total ?? null
}

/**
 * Get KH value for a specific NV + KH + column from aggregated data.
 */
export function getKHValue(
  aggregated: Map<string, AggregatedValues>,
  nvkd: string,
  maKh: string,
): number | null {
  const agg = aggregated.get(nvkd)
  if (!agg) return null
  return agg.kh[maKh] ?? null
}
