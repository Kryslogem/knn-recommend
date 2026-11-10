import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { get, send } from '../api/client'
import type { ModelVersion, TrainConfig, TrainingJob } from '../api/types'
import { PageTitle } from '../components/Layout'
import { Button, Card, ErrorState, Spinner, errText, useToast } from '../components/ui'

type Field = { key: keyof TrainConfig; label: string; min: number; max: number; int: boolean; hint: string }
const FIELDS: Field[] = [
  { key: 'k', label: 'K (số láng giềng)', min: 1, max: 200, int: true, hint: 'Tối đa K người giống nhất đã chấm phim' },
  { key: 'min_k', label: 'min_k', min: 1, max: 50, int: true, hint: 'Dưới ngưỡng này dùng điểm nền' },
  { key: 'shrinkage', label: 'shrinkage', min: 0, max: 5000, int: false, hint: 'Giảm độ tương đồng khi ít phim chung' },
  { key: 'min_support', label: 'min_support', min: 1, max: 50, int: true, hint: 'Số phim chung tối thiểu' },
  { key: 'reg_u', label: 'reg_u', min: 0, max: 500, int: false, hint: 'Regularization bias người dùng (ALS)' },
  { key: 'reg_i', label: 'reg_i', min: 0, max: 500, int: false, hint: 'Regularization bias phim (ALS)' },
  { key: 'n_epochs', label: 'n_epochs', min: 1, max: 50, int: true, hint: 'Số vòng ALS' },
  { key: 'min_item_ratings', label: 'min_item_ratings', min: 0, max: 1000, int: true, hint: 'Ngưỡng số rating của phim khi xếp hạng' },
]

const STATUS: Record<TrainingJob['status'], string> = { queued: 'bg-slate-100 text-slate-700', running: 'bg-amber-100 text-amber-800', succeeded: 'bg-emerald-100 text-emerald-800', failed: 'bg-red-100 text-red-800' }
const STATUS_VI: Record<TrainingJob['status'], string> = { queued: 'Đang chờ', running: 'Đang chạy', succeeded: 'Thành công', failed: 'Thất bại' }

export function DsTrain() {
  const qc = useQueryClient()
  const toast = useToast()
  const [form, setForm] = useState<Record<string, string>>({})
  const [selected, setSelected] = useState<number | null>(null)

  const models = useQuery({ queryKey: ['ds-models'], queryFn: () => get<{ items: ModelVersion[] }>('/ds/models') })
  const active = models.data?.items.find((m) => m.is_active)
  const defaults: Record<string, number> | null = active ? { ...active.config.params as Record<string, number>, ...active.config.serving } : null

  const jobs = useQuery({
    queryKey: ['ds-jobs'],
    queryFn: () => get<{ items: TrainingJob[] }>('/ds/training-jobs'),
    refetchInterval: (q) => (q.state.data?.items.some((j) => j.status === 'running' || j.status === 'queued') ? 2500 : false),
  })
  const detail = useQuery({
    queryKey: ['ds-job', selected],
    queryFn: () => get<TrainingJob>(`/ds/training-jobs/${selected}`),
    enabled: selected !== null,
    refetchInterval: (q) => (q.state.data && (q.state.data.status === 'running' || q.state.data.status === 'queued') ? 2000 : false),
  })

  const errors: Record<string, string> = {}
  for (const f of FIELDS) {
    const raw = form[f.key]
    if (raw === undefined || raw === '') continue
    const v = Number(raw)
    if (!Number.isFinite(v)) errors[f.key] = 'Phải là số'
    else if (f.int && !Number.isInteger(v)) errors[f.key] = 'Phải là số nguyên'
    else if (v < f.min || v > f.max) errors[f.key] = `Trong khoảng ${f.min}–${f.max}`
  }

  const start = useMutation({
    mutationFn: (body: Record<string, number>) => send<{ id: number }>('POST', '/ds/training-jobs', body),
    onSuccess: (r) => {
      toast('ok', `Đã tạo job #${r.id}`)
      setSelected(r.id)
      qc.invalidateQueries({ queryKey: ['ds-jobs'] })
    },
    onError: (e) => toast('err', errText(e)),
  })
  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (Object.keys(errors).length) return
    const body: Record<string, number> = {}
    for (const f of FIELDS) if (form[f.key] !== undefined && form[f.key] !== '') body[f.key] = Number(form[f.key])
    start.mutate(body)
  }
  const busy = jobs.data?.items.some((j) => j.status === 'running' || j.status === 'queued') ?? false

  return (
    <div className="space-y-6">
      <PageTitle title="Huấn luyện mô hình" subtitle="Fit KNNBaseline trên tập train, đánh giá trên validation rồi lưu thành một phiên bản mới (chưa kích hoạt). Ô để trống dùng cấu hình mặc định." />
      <Card title="Siêu tham số">
        <form onSubmit={submit} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4" noValidate>
          {FIELDS.map((f) => (
            <label key={f.key} className="block text-sm">
              <span className="font-medium">{f.label}</span>
              <input
                className={`mt-1 w-full rounded-md border px-3 py-1.5 ${errors[f.key] ? 'border-red-400' : 'border-slate-300'}`}
                inputMode="decimal"
                value={form[f.key] ?? ''}
                placeholder={defaults?.[f.key] !== undefined ? `đang dùng: ${defaults[f.key]}` : 'mặc định'}
                onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                aria-invalid={!!errors[f.key]}
              />
              <span className={`text-xs ${errors[f.key] ? 'text-red-600' : 'text-slate-500'}`}>{errors[f.key] ?? f.hint}</span>
            </label>
          ))}
          <div className="flex items-end sm:col-span-2 lg:col-span-4">
            <Button type="submit" disabled={start.isPending || busy || Object.keys(errors).length > 0}>
              {busy ? 'Đang có job chạy…' : 'Bắt đầu huấn luyện'}
            </Button>
          </div>
        </form>
        <p className="mt-3 text-xs text-slate-500">Job web không gắn metrics test; chỉ <code>scripts/evaluate.py</code> mới chạy test (một lần cho mỗi cấu hình đã chốt).</p>
      </Card>

      <Card title="Các job gần đây">
        {jobs.isLoading && <Spinner />}
        {jobs.error && <ErrorState error={jobs.error} retry={() => jobs.refetch()} />}
        {jobs.data && jobs.data.items.length === 0 && <p className="text-sm text-slate-500">Chưa có job nào.</p>}
        {jobs.data && jobs.data.items.length > 0 && (
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500"><tr><th>#</th><th>Trạng thái</th><th>Cấu hình</th><th>Bắt đầu</th><th /></tr></thead>
            <tbody>
              {jobs.data.items.map((j) => (
                <tr key={j.id} className={`border-t border-slate-100 ${selected === j.id ? 'bg-indigo-50' : ''}`}>
                  <td className="py-2">{j.id}</td>
                  <td><span className={`rounded-full px-2 py-0.5 text-xs ${STATUS[j.status]}`}>{STATUS_VI[j.status]}</span></td>
                  <td className="text-xs text-slate-600">K={j.config.knn.k}, min_k={j.config.knn.min_k}, shr={j.config.similarity.shrinkage}, reg={j.config.baseline.reg_u}/{j.config.baseline.reg_i}, thr={j.config.serving.min_item_ratings}</td>
                  <td className="text-xs text-slate-500">{j.started_at.replace('T', ' ').slice(0, 19)}</td>
                  <td><Button variant="ghost" onClick={() => setSelected(j.id)}>Xem log</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {selected !== null && (
          <div className="mt-4">
            <p className="mb-1 text-sm font-medium">Log job #{selected}</p>
            <pre className="max-h-64 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100" aria-label="Log huấn luyện">{detail.data?.log || (detail.isLoading ? 'Đang tải…' : '(chưa có log)')}</pre>
            {detail.data?.status === 'succeeded' && <p className="mt-2 text-sm text-emerald-700">Xong — vào “Phiên bản mô hình” để kích hoạt.</p>}
          </div>
        )}
      </Card>
    </div>
  )
}
