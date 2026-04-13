// ============================================================================
// STANDARDS: Số liệu & Định dạng
// - Dấu "," cho ngăn cách phần nghìn
// - Dấu "." cho thập phân
// - Viết gọn: >= 10,000 → "x nghìn", "x triệu", "x tỷ"
// - Null/undefined → "—"
// ============================================================================

// --- Number formatters (en-US locale: comma=thousands, dot=decimal) ---------

const NUM_INT = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
const NUM_DEC1 = new Intl.NumberFormat('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const NUM_DEC2 = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/**
 * Format number: 1234567 → "1,234,567"
 * @param decimals — số chữ số thập phân (mặc định 0)
 */
export function fmtNumber(v: number | null | undefined, decimals = 0): string {
  if (v == null || isNaN(v)) return '—'
  if (decimals === 0) return NUM_INT.format(Math.round(v))
  if (decimals === 1) return NUM_DEC1.format(v)
  if (decimals === 2) return NUM_DEC2.format(v)
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(v)
}

/**
 * Viết gọn số lớn cho label/chart.
 * >= 1,000,000,000 → "x tỷ"
 * >= 1,000,000     → "x triệu"
 * >= 10,000        → "x nghìn"
 * < 10,000         → format thường
 */
export function fmtCompact(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '—'
  const abs = Math.abs(v)
  const sign = v < 0 ? '-' : ''

  if (abs >= 1_000_000_000) {
    const n = abs / 1_000_000_000
    return `${sign}${stripTrailingZeros(n, 1)} tỷ`
  }
  if (abs >= 1_000_000) {
    const n = abs / 1_000_000
    return `${sign}${stripTrailingZeros(n, 1)} triệu`
  }
  if (abs >= 10_000) {
    const n = abs / 1_000
    return `${sign}${stripTrailingZeros(n, 1)} nghìn`
  }
  return fmtNumber(v)
}

/** Helper: "1.0" → "1", "1.5" → "1.5" */
function stripTrailingZeros(n: number, maxDecimals: number): string {
  const s = n.toFixed(maxDecimals)
  return s.replace(/\.0+$/, '')
}

/**
 * Parse raw input string → number (hỗ trợ cả dấu "," nghìn lẫn "." thập phân).
 * "1,234,567.89" → 1234567.89
 * "1234567"      → 1234567
 */
export function parseInputNumber(raw: string): number | null {
  const cleaned = raw.replace(/,/g, '').trim()
  if (cleaned === '' || cleaned === '-') return null
  const n = Number(cleaned)
  return isNaN(n) ? null : n
}

/**
 * Format raw input khi đang gõ → tự thêm dấu "," nghìn.
 * Giữ nguyên phần thập phân nếu có.
 * "1234567" → "1,234,567"
 * "1234.5"  → "1,234.5"
 */
export function formatInputOnType(raw: string): string {
  const negative = raw.startsWith('-')
  const stripped = raw.replace(/[^0-9.]/g, '')

  const parts = stripped.split('.')
  const intPart = parts[0] || ''
  const decPart = parts.length > 1 ? `.${parts[1]}` : ''

  // Add comma separators to integer part
  const formatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return `${negative ? '-' : ''}${formatted}${decPart}`
}

// --- Date formatters -------------------------------------------------------

/** Format date string: "2026-01-15" → "15/01/2026" */
export function fmtDate(s: string | null | undefined): string {
  if (!s) return ''
  const d = s.substring(0, 10)
  const [y, m, day] = d.split('-')
  return `${day}/${m}/${y}`
}

/** Extract ISO date: Date | string → "2026-01-15" */
export function isoDate(d: string | Date | null | undefined): string {
  if (!d) return ''
  if (typeof d === 'string') return d.substring(0, 10)
  return d.toISOString().substring(0, 10)
}

// --- Percent ---------------------------------------------------------------

/** Format percent: 0.85 → "85%", 0.856 → "85.6%" */
export function fmtPercent(v: number | null | undefined, decimals = 0): string {
  if (v == null || isNaN(v)) return '—'
  return `${(v * 100).toFixed(decimals)}%`
}

// --- CSS class for number styling ------------------------------------------

/** Get CSS class for number display: 'pos' | 'neg' | 'zero' */
export function numClass(v: number | null | undefined): string {
  if (v == null) return 'zero'
  const n = Math.round(v)
  if (n < 0) return 'neg'
  if (n === 0) return 'zero'
  return 'pos'
}

// --- Misc utilities --------------------------------------------------------

/** Escape HTML special characters */
export function escHtml(s: string | null | undefined): string {
  if (!s) return ''
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

/** Pad number: 1 → "01" */
export function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

/** Get today as ISO string */
export function today(): string {
  return new Date().toISOString().substring(0, 10)
}

/** Get first day of current month */
export function firstDayOfMonth(): string {
  const now = new Date()
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-01`
}
