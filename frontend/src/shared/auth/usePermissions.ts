import { useMemo } from 'react'
import type { User, NVNode, KhachHang } from '@/types'

interface PermissionResult {
  /** NV codes this user is allowed to see (empty = all) */
  userNvkdList: string[]
  /** BP codes this user is scoped to (empty = all) */
  userBpList: string[]
  /** Set of all allowed NV codes (computed from hierarchy) */
  allowedNV: Set<string>
  /** Compute allowed NV set from hierarchy — call after hierarchy loads */
  computeAllowedNV: (hierarchy: NVNode[], nvMap: Map<string, NVNode>) => Set<string>
  /** Get list of BP codes from KH data, filtered by user scope */
  getAllowedBP: (khMap: Map<string, KhachHang>) => string[]
}

export function usePermissions(user: User | null): PermissionResult {
  const userNvkdList = useMemo(
    () => (user?.maNvkdList ?? []).filter(Boolean),
    [user],
  )

  const userBpList = useMemo(
    () => (user?.maBp ?? []).filter(Boolean),
    [user],
  )

  function computeAllowedNV(
    hierarchy: NVNode[],
    nvMap: Map<string, NVNode>,
  ): Set<string> {
    if (!userNvkdList.length) {
      // No restriction — all NV allowed
      return new Set(hierarchy.map((h) => h.ma_nvkd))
    }

    const allowed = new Set<string>()

    function addDescendants(id: string) {
      allowed.add(id)
      const node = nvMap.get(id)
      if (node) {
        node.children.forEach((c) => addDescendants(c.ma_nvkd))
      }
    }

    userNvkdList.forEach((id) => {
      if (nvMap.has(id)) addDescendants(id)
    })

    return allowed
  }

  function getAllowedBP(khMap: Map<string, KhachHang>): string[] {
    if (userBpList.length) return [...userBpList].sort()

    const bps = new Set<string>()
    khMap.forEach((kh) => {
      if (kh.ma_bp) bps.add(kh.ma_bp)
    })
    return [...bps].sort()
  }

  return {
    userNvkdList,
    userBpList,
    allowedNV: new Set<string>(), // Will be computed after hierarchy loads
    computeAllowedNV,
    getAllowedBP,
  }
}
