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
    if (isRegister && !USERNAME_RE.test(name)) return setError('Username must be 3-32 characters: lowercase letters, digits, "_", "." or "-".')
    if (isRegister && password.length < 8) return setError('Password must be at least 8 characters.')
    setError(null)
    setBusy(true)
    try {
      const u = await (isRegister ? register : login)(name, password)
      const from = (loc.state as { from?: string } | null)?.from
      nav(isRegister ? '/onboarding' : from && from !== '/login' ? from : HOME_BY_ROLE[u.role], { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to sign in')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen">
      <div className="hazard" aria-hidden />
      <div className="mx-auto grid min-h-[calc(100vh-12px)] max-w-6xl grid-cols-1 gap-0 px-4 lg:grid-cols-[1.3fr_1fr]">
        <div className="flex flex-col justify-between border-ink py-8 lg:border-r-4 lg:pr-8">
          <p className="micro">Intelligent Systems / Assignment HK261</p>
          <div>
            <h1 className="display text-[clamp(4rem,13vw,10.5rem)]">
              KNN
              <br />
              /REC<sup className="align-top text-[0.18em]">®</sup>
            </h1>
            <p className="mt-6 max-w-md border-l-4 border-alert pl-4">
              A film recommender that finds viewers with a taste like yours, then learns how generously each of you rates. Built on MovieLens 100K and KNNBaseline.
            </p>
          </div>
          <div aria-hidden className="mt-8">
            <div className="barcode" />
            <p className="micro mt-2">Unit / D-01 · Rev 2.6</p>
          </div>
        </div>

        <form onSubmit={submit} className="flex flex-col justify-center gap-5 py-8 lg:pl-8" noValidate>
          <h2 className="h-sec">[ {isRegister ? 'Create account' : 'Sign in'} ]</h2>
          <label className="block">
            <span className="micro">Username</span>
            <input className="field mt-1" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoFocus required />
            {isRegister && <span className="micro mt-1 block opacity-70">Use a pseudonym. No real name or email is needed.</span>}
          </label>
          <label className="block">
            <span className="micro">Password</span>
            <input
              className="field mt-1"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={isRegister ? 'new-password' : 'current-password'}
              required
            />
          </label>
          {error && (
            <p role="alert" className="border-2 border-alert bg-alert p-2 font-bold text-white">
              /// {error}
            </p>
          )}
          <Button type="submit" disabled={busy || !username || !password}>
            {busy ? 'Working…' : isRegister ? 'Create account >>>' : 'Sign in >>>'}
          </Button>
          <p className="micro">
            {isRegister ? (
              <>
                Already registered? <Link to="/login" className="underline hover:text-alert">Sign in</Link>
              </>
            ) : (
              <>
                No account yet? <Link to="/register" className="underline hover:text-alert">Create one</Link>
              </>
            )}
          </p>
        </form>
      </div>
    </div>
  )
}

export const LoginPage = () => <AuthForm mode="login" />
export const RegisterPage = () => <AuthForm mode="register" />
