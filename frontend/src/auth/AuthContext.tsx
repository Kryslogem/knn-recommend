import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { TOKEN_KEY, UNAUTHORIZED_EVENT, get, send } from '../api/client'
import type { Role, TokenOut, User } from '../api/types'

type AuthState = {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<User>
  register: (username: string, password: string) => Promise<User>
  logout: () => void
  refresh: () => Promise<void>
}

const Ctx = createContext<AuthState | null>(null)

export const HOME_BY_ROLE: Record<Role, string> = { user: '/', admin: '/admin', data_scientist: '/ds' }

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(!!localStorage.getItem(TOKEN_KEY))

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
    qc.clear()
  }, [qc])

  const refresh = useCallback(async () => {
    setUser(await get<User>('/auth/me'))
  }, [])

  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) return
    get<User>('/auth/me')
      .then(setUser)
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const onUnauthorized = () => logout()
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [logout])

  const authenticate = useCallback(
    async (path: string, username: string, password: string) => {
      const out = await send<TokenOut>('POST', path, { username, password })
      qc.clear()
      localStorage.setItem(TOKEN_KEY, out.access_token)
      setUser(out.user)
      return out.user
    },
    [qc],
  )

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      login: (u, p) => authenticate('/auth/login', u, p),
      register: (u, p) => authenticate('/auth/register', u, p),
      logout,
      refresh,
    }),
    [user, loading, authenticate, logout, refresh],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useAuth must be used inside AuthProvider')
  return v
}
