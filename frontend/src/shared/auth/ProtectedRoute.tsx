import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './AuthProvider'
import { LoadingOverlay } from '@shared/ui/feedback/LoadingOverlay'

export function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) return <LoadingOverlay visible message="Đang kiểm tra phiên..." />
  if (!isAuthenticated) return <Navigate to="/login" replace />

  return <Outlet />
}
