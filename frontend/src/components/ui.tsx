import { createContext, useCallback, useContext, useEffect, useState, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { ApiError } from '../api/client'
import type { Source } from '../api/types'

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="max-w-sm p-4" role="status">
      <p className="micro mb-2">[ {label}… ]</p>
      <div className="loading-bar" />
    </div>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden />
}

export function SkeletonGrid({ n = 8 }: { n?: number }) {
  return (
    <div className="ruled grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" aria-hidden>
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className="h-40 bg-paper-2" />
      ))}
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="panel p-8">
      <p className="h-sec">[ {title} ]</p>
      {children && <div className="mt-2 max-w-xl">{children}</div>}
    </div>
  )
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  const msg = error instanceof Error ? error.message : 'Something went wrong'
  const code = error instanceof ApiError ? error.code : ''
  return (
    <div role="alert" className="border-2 border-alert">
      <div className="bg-alert px-3 py-1 micro font-bold text-white">/// Error {code && `· ${code}`}</div>
      <div className="p-3">
        <p className="font-bold">{msg}</p>
        {code === 'model_not_loaded' && <p className="mt-1">A data scientist needs to train and activate a model version.</p>}
        {retry && (
          <button onClick={retry} className="btn btn-sm mt-3">
            Retry
          </button>
        )}
      </div>
    </div>
  )
}

export function Button({ variant = 'primary', className = '', ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'danger' }) {
  const v = { primary: 'btn btn-solid', ghost: 'btn', danger: 'btn btn-alert' }[variant]
  return <button {...p} className={`${v} ${className}`} />
}

export function Card({ title, children, className = '' }: { title?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`panel ${className}`}>
      {title && <h2 className="panel-head">{title}</h2>}
      <div className="p-4">{children}</div>
    </section>
  )
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="p-4">
      <p className="micro">{label}</p>
      <p className="display num mt-2 text-4xl">{value}</p>
      {hint && <p className="micro mt-2 opacity-70">{hint}</p>}
    </div>
  )
}

const SOURCE: Record<Source, { label: string; cls: string; tip: string }> = {
  knn: { label: 'KNN', cls: 'tag tag-solid', tip: 'Predicted from people with similar taste' },
  baseline: { label: 'Baseline', cls: 'tag', tip: 'Not enough similar viewers: falls back to mu + user bias + item bias' },
  popular: { label: 'Popular', cls: 'tag', tip: 'No ratings from you yet, so this is a popular film' },
}
export function SourceBadge({ source }: { source: Source }) {
  const s = SOURCE[source]
  return (
    <span title={s.tip} className={s.cls}>
      {s.label}
    </span>
  )
}

export function Pagination({ page, pageSize, total, onChange }: { page: number; pageSize: number; total: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (pages <= 1) return null
  return (
    <nav className="mt-4 flex flex-wrap items-center gap-3" aria-label="Pagination">
      <Button variant="ghost" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        &lt;&lt; Prev
      </Button>
      <span className="micro num">
        Page {page} / {pages} · {total} results
      </span>
      <Button variant="ghost" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next &gt;&gt;
      </Button>
    </nav>
  )
}

export function useDebounce<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

// ---- Toast ----
type Toast = { id: number; kind: 'ok' | 'err'; text: string }
const ToastCtx = createContext<(kind: Toast['kind'], text: string) => void>(() => {})
// eslint-disable-next-line react-refresh/only-export-components
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([])
  const push = useCallback((kind: Toast['kind'], text: string) => {
    const id = Date.now() + Math.random()
    setItems((x) => [...x, { id, kind, text }])
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 4500)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex max-w-sm flex-col gap-2" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`border-2 border-ink px-3 py-2 font-bold ${t.kind === 'ok' ? 'bg-ink text-paper' : 'bg-alert text-white'}`}>
            <span className="micro mr-2">{t.kind === 'ok' ? '[ OK ]' : '[ ERROR ]'}</span>
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

export function errText(e: unknown): string {
  return e instanceof Error ? e.message : 'Something went wrong'
}
