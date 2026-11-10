import { useQuery } from '@tanstack/react-query'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { get } from '../api/client'
import type { Role } from '../api/types'
import { useAuth } from '../auth/AuthContext'

const NAV: Record<Role, { to: string; label: string; end?: boolean }[]> = {
  user: [
    { to: '/', label: 'Home', end: true },
    { to: '/movies', label: 'Catalog' },
    { to: '/recommendations', label: 'For you' },
    { to: '/history', label: 'My ratings' },
  ],
  admin: [
    { to: '/admin', label: 'Overview', end: true },
    { to: '/admin/users', label: 'Accounts' },
    { to: '/admin/movies', label: 'Catalog admin' },
    { to: '/movies', label: 'Browse as user' },
  ],
  data_scientist: [
    { to: '/ds', label: 'Data', end: true },
    { to: '/ds/train', label: 'Training' },
    { to: '/ds/models', label: 'Model versions' },
    { to: '/ds/evaluation', label: 'Evaluation' },
  ],
}
const ROLE_LABEL: Record<Role, string> = { user: 'User', admin: 'Admin', data_scientist: 'Data scientist' }

function Footer() {
  const health = useQuery({ queryKey: ['health'], queryFn: () => get<{ model_loaded: boolean; model_version: string | null }>('/health'), staleTime: 60000 })
  return (
    <footer className="mt-16 border-t-4 border-ink">
      <div className="barcode" aria-hidden />
      <div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-3 px-4 py-4 micro">
        <span>KNN/REC® · MovieLens 100K (1997-98) · Intelligent Systems HK261</span>
        <span className="num">Model / {health.data?.model_version ?? (health.data ? 'none loaded' : '…')}</span>
      </div>
    </footer>
  )
}

export function Layout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  if (!user) return null
  return (
    <div className="min-h-screen">
      <header>
        <div className="mx-auto flex max-w-6xl flex-wrap items-stretch justify-between gap-y-2 px-4 pt-4">
          <div className="flex items-end gap-3">
            <span className="display text-3xl">
              KNN/REC<sup className="text-sm">®</sup>
            </span>
            <span className="micro hidden pb-1 sm:inline">Film recommender / KNNBaseline</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="micro">
              {user.username} <span className="tag tag-solid ml-1">{ROLE_LABEL[user.role]}</span>
            </span>
            <button
              className="btn btn-sm"
              onClick={() => {
                logout()
                nav('/login')
              }}
            >
              Log out
            </button>
          </div>
        </div>
        <nav className="mx-auto mt-3 max-w-6xl px-4" aria-label="Main navigation">
          <ul className="flex flex-wrap border-2 border-ink">
            {NAV[user.role].map((n) => (
              <li key={n.to} className="border-r-2 border-ink last:border-r-0">
                <NavLink
                  to={n.to}
                  end={n.end}
                  className={({ isActive }) => `block px-4 py-2 micro font-bold ${isActive ? 'bg-ink text-paper' : 'hover:bg-paper-2'}`}
                >
                  {n.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="hazard mt-4" aria-hidden />
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}

export function PageTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-8 border-b-4 border-ink pb-4">
      <h1 className="display macro">{title}</h1>
      {subtitle && <p className="mt-3 max-w-3xl">&gt;&gt;&gt; {subtitle}</p>}
    </div>
  )
}
