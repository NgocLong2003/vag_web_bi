import type { HierarchyNode, NVNode } from '@/types'

/**
 * Build tree structure from flat hierarchy array.
 * Returns { roots, nvMap }
 */
export function buildTree(hierarchy: HierarchyNode[]): {
  roots: NVNode[]
  nvMap: Map<string, NVNode>
} {
  const nvMap = new Map<string, NVNode>()

  // Create nodes
  hierarchy.forEach((h) => {
    nvMap.set(h.ma_nvkd, { ...h, children: [] })
  })

  // Build parent-child relationships
  const roots: NVNode[] = []
  hierarchy.forEach((h) => {
    const node = nvMap.get(h.ma_nvkd)!
    if (h.ma_ql && nvMap.has(h.ma_ql)) {
      nvMap.get(h.ma_ql)!.children.push(node)
    } else {
      roots.push(node)
    }
  })

  // Sort by stt_nhom
  const sortFn = (a: NVNode, b: NVNode) => a.stt_nhom.localeCompare(b.stt_nhom)
  roots.sort(sortFn)
  nvMap.forEach((node) => node.children.sort(sortFn))

  return { roots, nvMap }
}

/**
 * Get all descendant IDs of a node (including itself).
 */
export function getDescendants(id: string, nvMap: Map<string, NVNode>): string[] {
  const result: string[] = []
  function walk(nodeId: string) {
    result.push(nodeId)
    const node = nvMap.get(nodeId)
    if (node) {
      node.children.forEach((c) => walk(c.ma_nvkd))
    }
  }
  walk(id)
  return result
}

/**
 * Get ancestors of a node (from self to root).
 */
export function getAncestors(id: string, nvMap: Map<string, NVNode>): string[] {
  const result: string[] = []
  let current = id
  const visited = new Set<string>()
  while (current && nvMap.has(current) && !visited.has(current)) {
    result.push(current)
    visited.add(current)
    current = nvMap.get(current)!.ma_ql
  }
  return result
}

/**
 * Walk tree depth-first, calling callback for each visible node.
 * Supports expand/collapse state.
 */
export function walkTree(
  roots: NVNode[],
  expanded: Set<string>,
  callback: (node: NVNode, depth: number, isLast: boolean, ancestors: { cont: boolean }[]) => void,
) {
  function walk(nodes: NVNode[], depth: number, ancestors: { cont: boolean }[]) {
    nodes.forEach((node, idx) => {
      const isLast = idx === nodes.length - 1
      callback(node, depth, isLast, [...ancestors])

      if (expanded.has(node.ma_nvkd) && node.children.length > 0) {
        walk(node.children, depth + 1, [...ancestors, { cont: !isLast }])
      }
    })
  }
  walk(roots, 0, [])
}

/**
 * Collapse single-child chains: if a node has no own data and only 1 visible child,
 * skip to that child (avoids unnecessary indentation).
 */
export function resolveNode(
  node: NVNode,
  hasOwnData: (node: NVNode) => boolean,
  allowedNV: Set<string>,
): NVNode {
  const visibleKids = node.children.filter((c) => allowedNV.has(c.ma_nvkd))
  if (!hasOwnData(node) && visibleKids.length === 1) {
    return resolveNode(visibleKids[0], hasOwnData, allowedNV)
  }
  return node
}
