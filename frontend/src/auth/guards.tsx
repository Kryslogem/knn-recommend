import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { Role } from '../api/types'
import { Spinner } from '../components/ui'
import { useAuth } from './AuthContext'

/** Signed-in users only; a role outside `roles` is sent to the 403 page. */
export function RoleRoute({ roles }: { roles?: Role[] }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <Spinner label="Checking session" />
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  if (roles && !roles.includes(user.role)) return <Navigate to="/forbidden" replace />
  return <Outlet />
}
