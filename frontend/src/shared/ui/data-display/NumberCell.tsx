import { fmtNumber, numClass } from '@shared/utils/format'

interface NumberCellProps {
  value: number | null | undefined
  /** Additional CSS class: 'sub' for subtotal, 'grand' for grand total */
  variant?: '' | 'sub' | 'grand'
  /** If true, positive numbers are shown as negative (red) and vice versa — for debt columns */
  invert?: boolean
  /** Show shimmer skeleton if data is loading */
  loading?: boolean
}

/**
 * NumberCell — formatted number display for report tables.
 * Handles positive/negative/zero styling, loading states, and null values.
 */
export function NumberCell({ value, variant = '', invert = false, loading = false }: NumberCellProps) {
  if (loading) {
    return <span className="skeleton" />
  }

  if (value == null) {
    return <span className="font-mono text-xs text-surface-3">—</span>
  }

  const n = Math.round(value)
  let cls: string

  if (invert) {
    cls = n > 0 ? 'neg' : n < 0 ? 'pos' : 'zero'
  } else {
    cls = numClass(value)
  }

  return <span className={`n ${cls} ${variant}`}>{fmtNumber(value)}</span>
}
