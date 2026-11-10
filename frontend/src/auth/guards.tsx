import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { Role } from '../api/types'
import { Spinner } from '../components/ui'
import { useAuth } from './AuthContext'

/** Chỉ cho người đã đăng nhập; nếu role không nằm trong `roles` thì chuyển sang trang 403. */
export function RoleRoute({ roles }: { roles?: Role[] }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <Spinner label="Đang kiểm tra phiên đăng nhập…" />
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  if (roles && !roles.includes(user.role)) return <Navigate to="/forbidden" replace />
  return <Outlet />
}
