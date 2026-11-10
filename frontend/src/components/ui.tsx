import { createContext, useCallback, useContext, useEffect, useState, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { ApiError } from '../api/client'
import type { Source } from '../api/types'

export function Spinner({ label = 'Đang tải…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 p-6 text-slate-500" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600" />
      {label}
    </div>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-slate-200 ${className}`} />
}

export function SkeletonGrid({ n = 8 }: { n?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" aria-hidden>
      {Array.from({ length: n }, (_, i) => (
        <Skeleton key={i} className="h-40" />
      ))}
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
      <p className="font-medium text-slate-700">{title}</p>
      {children && <div className="mt-2 text-sm text-slate-500">{children}</div>}
    </div>
  )
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  const msg = error instanceof ApiError ? error.message : error instanceof Error ? error.message : 'Đã xảy ra lỗi'
  const code = error instanceof ApiError ? error.code : ''
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      <p className="font-medium">{msg}</p>
      {code === 'model_not_loaded' && <p className="mt-1">Nhờ Data Scientist huấn luyện và kích hoạt một phiên bản mô hình.</p>}
      {retry && (
        <button onClick={retry} className="mt-2 rounded border border-red-300 bg-white px-2 py-1 hover:bg-red-100">
          Thử lại
        </button>
      )}
    </div>
  )
}

export function Button({ variant = 'primary', className = '', ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'danger' }) {
  const styles = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-300',
    ghost: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:text-slate-400',
    danger: 'bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300',
  }[variant]
  return <button {...p} className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed ${styles} ${className}`} />
}

export function Card({ title, children, className = '' }: { title?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-slate-200 bg-white p-4 shadow-sm ${className}`}>
      {title && <h2 className="mb-3 font-semibold text-slate-800">{title}</h2>}
      {children}
    </section>
  )
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

const SOURCE_STYLE: Record<Source, { label: string; cls: string; tip: string }> = {
  knn: { label: 'KNN', cls: 'bg-indigo-100 text-indigo-800', tip: 'Dự đoán từ những người có gu giống bạn' },
  baseline: { label: 'Điểm nền', cls: 'bg-amber-100 text-amber-800', tip: 'Không đủ láng giềng nên dùng điểm nền μ + b_user + b_item' },
  popular: { label: 'Phổ biến', cls: 'bg-emerald-100 text-emerald-800', tip: 'Chưa có đánh giá của bạn nên hiện phim phổ biến' },
}
export function SourceBadge({ source }: { source: Source }) {
  const s = SOURCE_STYLE[source]
  return (
    <span title={s.tip} className={`rounded-full px-2 py-0.5 text-xs font-medium ${s.cls}`}>
      {s.label}
    </span>
  )
}

export function Pagination({ page, pageSize, total, onChange }: { page: number; pageSize: number; total: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (pages <= 1) return null
  return (
    <nav className="mt-4 flex items-center justify-center gap-3 text-sm" aria-label="Phân trang">
      <Button variant="ghost" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← Trước
      </Button>
      <span className="text-slate-600">
        Trang {page}/{pages} · {total} kết quả
      </span>
      <Button variant="ghost" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Sau →
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
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 4000)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`rounded-md px-4 py-2 text-sm text-white shadow-lg ${t.kind === 'ok' ? 'bg-emerald-600' : 'bg-red-600'}`}>
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

export function errText(e: unknown): string {
  return e instanceof Error ? e.message : 'Đã xảy ra lỗi'
}
