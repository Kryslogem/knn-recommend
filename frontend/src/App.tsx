import { lazy, Suspense } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { HOME_BY_ROLE, useAuth } from './auth/AuthContext'
import { RoleRoute } from './auth/guards'
import { Layout } from './components/Layout'
import { AdminMovies, AdminOverview, AdminUsers } from './pages/AdminPages'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import { HistoryPage } from './pages/HistoryPage'
import { HomePage } from './pages/HomePage'
import { MovieDetailPage } from './pages/MovieDetailPage'
import { MoviesPage } from './pages/MoviesPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { RecommendationsPage } from './pages/RecommendationsPage'
import { Spinner } from './components/ui'

// Các trang Data Scientist kéo theo thư viện biểu đồ nặng → tải theo yêu cầu.
const DsOverview = lazy(() => import('./pages/DsData').then((m) => ({ default: m.DsOverview })))
const DsEvaluation = lazy(() => import('./pages/DsEvaluation').then((m) => ({ default: m.DsEvaluation })))
const DsModels = lazy(() => import('./pages/DsModels').then((m) => ({ default: m.DsModels })))
const DsTrain = lazy(() => import('./pages/DsTrain').then((m) => ({ default: m.DsTrain })))

function Message({ title, text }: { title: string; text: string }) {
  const { user } = useAuth()
  return (
    <div className="py-16 text-center">
      <h1 className="text-3xl font-bold text-slate-800">{title}</h1>
      <p className="mt-2 text-slate-500">{text}</p>
      <Link to={user ? HOME_BY_ROLE[user.role] : '/login'} className="mt-4 inline-block text-indigo-700 underline">
        Về trang chính
      </Link>
    </div>
  )
}

/** Trang chủ "/" chỉ dành cho người dùng thường; admin và Data Scientist chuyển về trang của vai trò mình. */
function Home() {
  const { user } = useAuth()
  if (user && user.role !== 'user') return <Navigate to={HOME_BY_ROLE[user.role]} replace />
  return <HomePage />
}

export default function App() {
  return (
    <Suspense fallback={<Spinner />}>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<RoleRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/forbidden" element={<Message title="403" text="Bạn không có quyền truy cập trang này." />} />
          <Route path="/movies" element={<MoviesPage />} />
          <Route path="/movies/:id" element={<MovieDetailPage />} />

          <Route element={<RoleRoute roles={['user']} />}>
            <Route path="/onboarding" element={<OnboardingPage />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            <Route path="/history" element={<HistoryPage />} />
          </Route>

          <Route element={<RoleRoute roles={['admin']} />}>
            <Route path="/admin" element={<AdminOverview />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/movies" element={<AdminMovies />} />
          </Route>

          <Route element={<RoleRoute roles={['data_scientist']} />}>
            <Route path="/ds" element={<DsOverview />} />
            <Route path="/ds/train" element={<DsTrain />} />
            <Route path="/ds/models" element={<DsModels />} />
            <Route path="/ds/evaluation" element={<DsEvaluation />} />
          </Route>

          <Route path="*" element={<Message title="404" text="Không tìm thấy trang." />} />
        </Route>
      </Route>
    </Routes>
    </Suspense>
  )
}
