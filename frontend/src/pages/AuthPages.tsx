import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { HOME_BY_ROLE, useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui'

const USERNAME_RE = /^[a-z0-9_.-]{3,32}$/

function AuthForm({ mode }: { mode: 'login' | 'register' }) {
  const { user, login, register } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={HOME_BY_ROLE[user.role]} replace />

  const isRegister = mode === 'register'
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const name = username.trim().toLowerCase()
    if (isRegister && !USERNAME_RE.test(name)) return setError('Tên đăng nhập gồm 3–32 ký tự: chữ thường, số, "_", "." hoặc "-".')
    if (isRegister && password.length < 8) return setError('Mật khẩu cần ít nhất 8 ký tự.')
    setError(null)
    setBusy(true)
    try {
      const u = await (isRegister ? register : login)(name, password)
      const from = (loc.state as { from?: string } | null)?.from
      nav(isRegister ? '/onboarding' : from && from !== '/login' ? from : HOME_BY_ROLE[u.role], { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Không thể đăng nhập')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" noValidate>
        <div>
          <h1 className="text-xl font-bold text-indigo-700">🎬 KNN Movie Recommender</h1>
          <p className="text-sm text-slate-500">{isRegister ? 'Tạo tài khoản để nhận đề xuất phim' : 'Đăng nhập để tiếp tục'}</p>
        </div>
        <label className="block text-sm">
          Tên đăng nhập
          <input
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
          {isRegister && <span className="text-xs text-slate-500">Dùng tên giả danh; hệ thống không cần tên thật hay email.</span>}
        </label>
        <label className="block text-sm">
          Mật khẩu
          <input
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            required
          />
        </label>
        {error && (
          <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <Button type="submit" disabled={busy || !username || !password} className="w-full">
          {busy ? 'Đang xử lý…' : isRegister ? 'Đăng ký' : 'Đăng nhập'}
        </Button>
        <p className="text-center text-sm text-slate-600">
          {isRegister ? (
            <>
              Đã có tài khoản? <Link to="/login" className="text-indigo-700 underline">Đăng nhập</Link>
            </>
          ) : (
            <>
              Chưa có tài khoản? <Link to="/register" className="text-indigo-700 underline">Đăng ký</Link>
            </>
          )}
        </p>
      </form>
    </div>
  )
}

export const LoginPage = () => <AuthForm mode="login" />
export const RegisterPage = () => <AuthForm mode="register" />
