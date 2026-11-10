// Backend client. Every path goes through the Vite /api proxy.
const BASE = '/api/v1'
export const TOKEN_KEY = 'token'
export const UNAUTHORIZED_EVENT = 'knn:unauthorized'

export class ApiError extends Error {
  status: number
  code: string
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY)
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, 'network', 'Cannot reach the server. Check that the backend is running.')
  }
  if (!res.ok) {
    let detail = res.statusText
    let code = `http_${res.status}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
      if (typeof body.code === 'string') code = body.code
    } catch {
      /* body is not JSON */
    }
    // Expired/invalid token: sign out (does not apply to a wrong-password login)
    if (res.status === 401 && token && !path.startsWith('/auth/login')) {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    }
    throw new ApiError(res.status, code, detail)
  }
  return res.json() as Promise<T>
}

export const get = <T>(path: string) => api<T>(path)
export const send = <T>(method: string, path: string, body?: unknown) =>
  api<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) })

export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') p.set(k, String(v))
  const s = p.toString()
  return s ? `?${s}` : ''
}
