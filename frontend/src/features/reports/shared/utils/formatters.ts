// ============================================================================
// Formatters — Định dạng số, ngày, tiền tệ
// Dùng chung cho mọi báo cáo
// ============================================================================

/** Định dạng số có dấu phân cách hàng nghìn (VN style: 1.234.567) */
export function fmtV(value: number | null | undefined): string {
  if (value == null) return '—'
  const n = Math.round(value)
  if (n === 0) return '0'
  return n.toLocaleString('vi-VN')
}

/** Định dạng ngày ISO → dd/mm/yyyy */
export function fmtD(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    const dd = String(d.getDate()).padStart(2, '0')
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const yyyy = d.getFullYear()
    return `${dd}/${mm}/${yyyy}`
  } catch {
    return dateStr
  }
}

/** Chuyển ngày dạng dd/mm/yyyy hoặc Date → yyyy-mm-dd (ISO) */
export function toISO(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  if (dateStr.includes('-') && dateStr.length >= 10) return dateStr.substring(0, 10)
  const parts = dateStr.split('/')
  if (parts.length === 3) return `${parts[2]}-${parts[1]}-${parts[0]}`
  return dateStr
}

/** CSS class cho giá trị số: pos / neg / zero */
export function numClass(value: number, isInverse = false): string {
  const n = Math.round(value)
  if (n === 0) return 'zero'
  if (isInverse) return n < 0 ? 'pos' : 'neg'  // Dư nợ: âm = tốt
  return n < 0 ? 'neg' : 'pos'
}

/** Render HTML cho ô số (dùng trong dangerouslySetInnerHTML) */
export function numHTML(
  value: number | null | undefined,
  extraClass = '',
  isInverse = false,
): string {
  if (value == null) return '<span class="dash">—</span>'
  const n = Math.round(value)
  const cls = numClass(n, isInverse)
  return `<span class="n ${cls} ${extraClass}">${fmtV(n)}</span>`
}

/** Shimmer HTML cho ô đang loading */
export function shimmerHTML(): string {
  return '<span class="skeleton" style="width:55px;height:10px"></span>'
}
/** Alias ngắn — tương thích code cũ */
export const shimH = shimmerHTML
export const iso = toISO

/** Escape HTML entities */
export function escHTML(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

/** Thời gian tương đối: "5 phút trước", "2 giờ trước" */
export function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr || dateStr === 'None') return ''
  try {
    const diff = Date.now() - new Date(dateStr).getTime()
    const m = Math.floor(diff / 60000)
    if (m < 1) return 'vừa xong'
    if (m < 60) return `${m} phút trước`
    const h = Math.floor(m / 60)
    if (h < 24) return `${h} giờ trước`
    return `${Math.floor(h / 24)} ngày trước`
  } catch {
    return ''
  }
}