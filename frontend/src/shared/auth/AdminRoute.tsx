import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './AuthProvider'

export function AdminRoute() {
  const { user } = useAuth()

  if (user && user.role !== 'admin') {
    return <Navigate to="/dashboards" replace />
  }

  return <Outlet />
}
