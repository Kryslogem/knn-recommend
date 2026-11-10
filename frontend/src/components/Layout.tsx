import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import type { Role } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { Button } from './ui'

const NAV: Record<Role, { to: string; label: string; end?: boolean }[]> = {
  user: [
    { to: '/', label: 'Trang chủ', end: true },
    { to: '/movies', label: 'Danh mục phim' },
    { to: '/recommendations', label: 'Đề xuất' },
    { to: '/history', label: 'Lịch sử của tôi' },
  ],
  admin: [
    { to: '/admin', label: 'Tổng quan', end: true },
    { to: '/admin/users', label: 'Tài khoản' },
    { to: '/admin/movies', label: 'Danh mục phim' },
    { to: '/movies', label: 'Xem như người dùng' },
  ],
  data_scientist: [
    { to: '/ds', label: 'Dữ liệu', end: true },
    { to: '/ds/train', label: 'Huấn luyện' },
    { to: '/ds/models', label: 'Phiên bản mô hình' },
    { to: '/ds/evaluation', label: 'Đánh giá' },
  ],
}
const ROLE_LABEL: Record<Role, string> = { user: 'Người dùng', admin: 'Quản trị viên', data_scientist: 'Data Scientist' }

export function Layout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  if (!user) return null
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <span className="font-bold text-indigo-700">🎬 KNN Movie Recommender</span>
          <nav className="flex flex-wrap gap-1" aria-label="Điều hướng chính">
            {NAV[user.role].map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) => `rounded-md px-3 py-1.5 text-sm ${isActive ? 'bg-indigo-50 font-medium text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`}
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="text-slate-600">
              {user.username} <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{ROLE_LABEL[user.role]}</span>
            </span>
            <Button
              variant="ghost"
              onClick={() => {
                logout()
                nav('/login')
              }}
            >
              Đăng xuất
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}

export function PageTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-5">
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
    </div>
  )
}
