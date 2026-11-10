import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { get, send } from '../api/client'
import type { ModelVersion, TrainConfig, TrainingJob } from '../api/types'
import { PageTitle } from '../components/Layout'
import { Button, Card, ErrorState, Spinner, errText, useToast } from '../components/ui'

type Field = { key: keyof TrainConfig; label: string; min: number; max: number; int: boolean; hint: string }
const FIELDS: Field[] = [
  { key: 'k', label: 'K (neighbours)', min: 1, max: 200, int: true, hint: 'Use at most K most-similar viewers who rated the film' },
  { key: 'min_k', label: 'min_k', min: 1, max: 50, int: true, hint: 'Below this many neighbours, use the baseline' },
  { key: 'shrinkage', label: 'shrinkage', min: 0, max: 5000, int: false, hint: 'Damps similarity when few films are shared' },
  { key: 'min_support', label: 'min_support', min: 1, max: 50, int: true, hint: 'Minimum films two viewers must share' },
  { key: 'reg_u', label: 'reg_u', min: 0, max: 500, int: false, hint: 'ALS regularization of user bias' },
  { key: 'reg_i', label: 'reg_i', min: 0, max: 500, int: false, hint: 'ALS regularization of film bias' },
  { key: 'n_epochs', label: 'n_epochs', min: 1, max: 50, int: true, hint: 'Number of ALS sweeps' },
  { key: 'min_item_ratings', label: 'min_item_ratings', min: 0, max: 1000, int: true, hint: 'Minimum training ratings for a film to be ranked' },
]

const STATUS_TAG: Record<TrainingJob['status'], string> = { queued: 'tag', running: 'tag tag-solid', succeeded: 'tag', failed: 'tag tag-alert' }
const STATUS_LABEL: Record<TrainingJob['status'], string> = { queued: 'Queued', running: 'Running', succeeded: 'Succeeded', failed: 'Failed' }

export function DsTrain() {
  const qc = useQueryClient()
  const toast = useToast()
  const [form, setForm] = useState<Record<string, string>>({})
  const [selected, setSelected] = useState<number | null>(null)

  const models = useQuery({ queryKey: ['ds-models'], queryFn: () => get<{ items: ModelVersion[] }>('/ds/models') })
  const active = models.data?.items.find((m) => m.is_active)
  const defaults: Record<string, number> | null = active ? { ...(active.config.params as Record<string, number>), ...active.config.serving } : null

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
    if (!Number.isFinite(v)) errors[f.key] = 'Must be a number'
    else if (f.int && !Number.isInteger(v)) errors[f.key] = 'Must be a whole number'
    else if (v < f.min || v > f.max) errors[f.key] = `Must be between ${f.min} and ${f.max}`
  }

  const start = useMutation({
    mutationFn: (body: Record<string, number>) => send<{ id: number }>('POST', '/ds/training-jobs', body),
    onSuccess: (r) => {
      toast('ok', `Job #${r.id} created`)
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
    <div className="space-y-8">
      <PageTitle title="Training" subtitle="Fit KNNBaseline on the train split, evaluate on validation, then save a new model version (not activated yet). Leave a field empty to use the current default." />
      <Card title="Hyperparameters">
        <form onSubmit={submit} className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4" noValidate>
          {FIELDS.map((f) => (
            <label key={f.key} className="block">
              <span className="micro font-bold">{f.label}</span>
              <input
                className="field mt-1"
                inputMode="decimal"
                value={form[f.key] ?? ''}
                placeholder={defaults?.[f.key] !== undefined ? `current: ${defaults[f.key]}` : 'default'}
                onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                aria-invalid={!!errors[f.key]}
              />
              <span className={`micro mt-1 block ${errors[f.key] ? 'font-bold text-alert' : 'opacity-70'}`}>{errors[f.key] ?? f.hint}</span>
            </label>
          ))}
          <div className="flex items-end sm:col-span-2 lg:col-span-4">
            <Button type="submit" disabled={start.isPending || busy || Object.keys(errors).length > 0}>
              {busy ? 'A job is running…' : 'Start training >>>'}
            </Button>
          </div>
        </form>
        <p className="micro mt-4 opacity-70">Web jobs never attach test metrics. Only <code>scripts/evaluate.py</code> runs the test set, once per frozen configuration.</p>
      </Card>

      <Card title="Recent jobs">
        {jobs.isLoading && <Spinner />}
        {jobs.error && <ErrorState error={jobs.error} retry={() => jobs.refetch()} />}
        {jobs.data && jobs.data.items.length === 0 && <p>No jobs yet.</p>}
        {jobs.data && jobs.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Status</th>
                  <th>Configuration</th>
                  <th>Started (UTC)</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {jobs.data.items.map((j) => (
                  <tr key={j.id} className={selected === j.id ? 'bg-paper-2' : ''}>
                    <td className="num font-bold">{j.id}</td>
                    <td>
                      <span className={STATUS_TAG[j.status]}>{STATUS_LABEL[j.status]}</span>
                    </td>
                    <td className="micro num">
                      K={j.config.knn.k} min_k={j.config.knn.min_k} shr={j.config.similarity.shrinkage} reg={j.config.baseline.reg_u}/{j.config.baseline.reg_i} thr={j.config.serving.min_item_ratings}
                    </td>
                    <td className="micro num">{j.started_at.replace('T', ' ').slice(0, 19)}</td>
                    <td>
                      <Button variant="ghost" className="btn-sm" onClick={() => setSelected(j.id)}>
                        View log
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {selected !== null && (
          <div className="mt-5">
            <p className="micro mb-1 font-bold">Log / job #{selected}</p>
            <pre className="max-h-64 overflow-auto border-2 border-ink bg-ink p-3 text-paper" aria-label="Training log">
              {detail.data?.log || (detail.isLoading ? 'Loading…' : '(no log yet)')}
            </pre>
            {detail.data?.status === 'succeeded' && <p className="mt-2 font-bold">&gt;&gt;&gt; Done. Open "Model versions" to activate it.</p>}
          </div>
        )}
      </Card>
    </div>
  )
}
