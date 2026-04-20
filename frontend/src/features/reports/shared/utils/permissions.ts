// ============================================================================
// Permissions — Lọc nhân viên, khách hàng theo quyền user
// Dùng chung cho mọi báo cáo
// ============================================================================

import type { NVNode, KHRaw } from '../components/TreeTable/types'

/** Parse chuỗi hoặc mảng → mảng trimmed */
export function parseList(raw: string | string[] | null | undefined): string[] {
  if (!raw) return []
  if (Array.isArray(raw)) return raw.map(s => s.trim()).filter(Boolean)
  return raw.split(',').map(s => s.trim()).filter(Boolean)
}

/** Tính danh sách mã NVKD mà user được phép xem */
export function computeAllowedNV(
  hierarchy: NVNode[],
  userNvkdList: string[],
): Set<string> {
  if (!userNvkdList.length) {
    // Không giới hạn → cho phép tất cả
    return new Set(hierarchy.map(n => n.ma_nvkd))
  }

  const allowed = new Set<string>()
  const nvMap = new Map(hierarchy.map(n => [n.ma_nvkd, n]))

  // Thêm user và tất cả con cháu
  function addWithDescendants(maNvkd: string) {
    if (allowed.has(maNvkd)) return
    const node = nvMap.get(maNvkd)
    if (!node) return
    allowed.add(maNvkd)
    node.children.forEach(c => addWithDescendants(c.ma_nvkd))
  }

  // Thêm user và tất cả cha ông (để hiện tree)
  function addWithAncestors(maNvkd: string) {
    let current = nvMap.get(maNvkd)
    while (current) {
      allowed.add(current.ma_nvkd)
      current = current.ma_ql ? nvMap.get(current.ma_ql) : undefined
    }
  }

  userNvkdList.forEach(id => {
    addWithDescendants(id)
    addWithAncestors(id)
  })

  return allowed
}

/** Lọc bộ phận được phép xem — derive từ khMap nếu user không bị giới hạn */
export function getAllowedBP(
  userMaBP: string | string[] | null | undefined,
  khMap: Map<string, { ma_bp?: string }>,
): string[] {
  const userBPs = parseList(userMaBP)
  if (userBPs.length) return userBPs.sort()
  // Không giới hạn → lấy tất cả BP từ danh sách khách hàng
  const bpSet = new Set<string>()
  khMap.forEach(kh => {
    if (kh.ma_bp) bpSet.add(kh.ma_bp)
  })
  return [...bpSet].sort()
}