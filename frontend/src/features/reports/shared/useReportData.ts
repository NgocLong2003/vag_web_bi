import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { apiClient } from '@shared/api/client'
import { useAuth } from '@shared/auth/AuthProvider'
import { usePermissions } from '@shared/auth/usePermissions'
import { buildTree } from '@shared/utils/tree'
import type { HierarchyNode, KhachHang, ApiResponse } from '@/types'
import type { ReportInitData } from './report.types'

interface UseReportDataOptions {
  /** API endpoint for hierarchy */
  hierarchyUrl: string
  /** API endpoint for khach hang */
  khachhangUrl: string
  /** Enable queries */
  enabled?: boolean
}

/**
 * useReportData — loads hierarchy + KH + computes permissions.
 * Shared across all tree-based reports (Kinh Doanh, Khách Hàng, Chi Tiết).
 */
export function useReportData({ hierarchyUrl, khachhangUrl, enabled = true }: UseReportDataOptions): {
  data: ReportInitData | null
  isLoading: boolean
  error: string | null
} {
  const { user } = useAuth()
  const permissions = usePermissions(user)

  const hierarchyQuery = useQuery({
    queryKey: ['hierarchy', hierarchyUrl],
    queryFn: () => apiClient.get<ApiResponse<HierarchyNode[]>>(hierarchyUrl),
    enabled,
    staleTime: 10 * 60 * 1000, // 10 min — hierarchy rarely changes
  })

  const khQuery = useQuery({
    queryKey: ['khachhang', khachhangUrl],
    queryFn: () => apiClient.get<ApiResponse<KhachHang[]>>(khachhangUrl),
    enabled,
    staleTime: 10 * 60 * 1000,
  })

  const data = useMemo<ReportInitData | null>(() => {
    if (!hierarchyQuery.data?.success || !khQuery.data?.success) return null

    const { roots, nvMap } = buildTree(hierarchyQuery.data.data)
    const allowedNV = permissions.computeAllowedNV(
      Array.from(nvMap.values()),
      nvMap,
    )

    const khMap = new Map<string, KhachHang>()
    const khNames = new Map<string, string>()
    khQuery.data.data.forEach((kh) => {
      if (kh.ma_kh) {
        khMap.set(kh.ma_kh, kh)
        khNames.set(kh.ma_kh, kh.ten_kh)
      }
    })

    const allowedBP = permissions.getAllowedBP(khMap)

    return { hierarchy: hierarchyQuery.data.data, nvMap, roots, khMap, khNames, allowedNV, allowedBP }
  }, [hierarchyQuery.data, khQuery.data, permissions])

  const isLoading = hierarchyQuery.isLoading || khQuery.isLoading
  const error = hierarchyQuery.error?.message || khQuery.error?.message || null

  return { data, isLoading, error }
}
