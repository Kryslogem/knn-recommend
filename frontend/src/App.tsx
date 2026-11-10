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

// Data scientist pages pull in the heavy chart library, so load them on demand.
const DsOverview = lazy(() => import('./pages/DsData').then((m) => ({ default: m.DsOverview })))
const DsEvaluation = lazy(() => import('./pages/DsEvaluation').then((m) => ({ default: m.DsEvaluation })))
const DsModels = lazy(() => import('./pages/DsModels').then((m) => ({ default: m.DsModels })))
const DsTrain = lazy(() => import('./pages/DsTrain').then((m) => ({ default: m.DsTrain })))

function Message({ title, text }: { title: string; text: string }) {
  const { user } = useAuth()
  return (
    <div className="py-16">
      <h1 className="display text-[clamp(5rem,18vw,14rem)]">{title}</h1>
      <p className="mt-4 max-w-xl border-l-4 border-alert pl-4">{text}</p>
      <Link to={user ? HOME_BY_ROLE[user.role] : '/login'} className="btn mt-6">
        Back to start
      </Link>
    </div>
  )
}

/** "/" is for regular users only; admins and data scientists are sent to their own home. */
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
          <Route path="/forbidden" element={<Message title="403" text="You do not have permission to open this page." />} />
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

          <Route path="*" element={<Message title="404" text="Page not found." />} />
        </Route>
      </Route>
    </Routes>
    </Suspense>
  )
}
