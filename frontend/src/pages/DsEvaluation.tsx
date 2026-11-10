import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { get } from '../api/client'
import type { CompareRow, Comparison, ErrorAnalysis, GroupRow, TuningRow } from '../api/types'
import { PageTitle } from '../components/Layout'
import { Card, ErrorState, Spinner } from '../components/ui'
import { ALERT, GRID_STROKE, INK, MUTED, SERIES, TOOLTIP_STYLE } from './chartStyle'

const f4 = (x: unknown) => (typeof x === 'number' ? x.toFixed(4) : '-')

// Keyed by the stable model id so labels stay English even for results generated before the UI was translated.
const MODEL_LABEL: Record<string, string> = {
  popular: '1. Popular films',
  bias_only: '2. Bias only',
  knn_basic: '3. KNNBasic (plain Pearson)',
  knn_baseline_no_shrinkage: '4. KNNBaseline, no shrinkage',
  knn_baseline: '5. KNNBaseline (full)',
}
const labelOf = (r: CompareRow) => MODEL_LABEL[r.model] ?? r.label

function CompareTable({ rows, thr }: { rows: CompareRow[]; thr: number }) {
  const cols: { key: string; label: string; best: 'min' | 'max' }[] = [
    { key: 'rmse', label: 'RMSE', best: 'min' },
    { key: 'mae', label: 'MAE', best: 'min' },
    { key: `precision@10_min${thr}`, label: `P@10 (>=${thr})`, best: 'max' },
    { key: `recall@10_min${thr}`, label: `R@10 (>=${thr})`, best: 'max' },
    { key: `ndcg@10_min${thr}`, label: `NDCG@10 (>=${thr})`, best: 'max' },
    { key: 'ndcg@10', label: 'NDCG@10 (unfiltered)', best: 'max' },
    { key: `catalog_coverage_min${thr}`, label: 'Catalog coverage', best: 'max' },
    { key: 'prediction_coverage_knn', label: 'Predicted by KNN', best: 'max' },
  ]
  const best = (key: string, mode: 'min' | 'max') => {
    const v = rows.map((r) => r[key] as number)
    return mode === 'min' ? Math.min(...v) : Math.max(...v)
  }
  return (
    <div className="overflow-x-auto">
      <table className="table">
        <thead>
          <tr>
            <th>Model</th>
            {cols.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.model} className="num">
              <td className="font-bold">{labelOf(r)}</td>
              {cols.map((c) => {
                const v = r[c.key] as number
                const isBest = v === best(c.key, c.best)
                return (
                  <td key={c.key} className={isBest ? 'bg-ink font-bold text-paper' : ''}>
                    {f4(v)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="micro mt-3 opacity-70">
        Inverted cell = best in the column. MAE and RMSE cover every held-out pair, including pairs that had to fall back. Ranking metrics cover users with at least one relevant film (rated 4 or more).
      </p>
    </div>
  )
}

function GroupChart({ title, rows }: { title: string; rows: GroupRow[] }) {
  return (
    <Card title={title}>
      <div className="h-56">
        <ResponsiveContainer>
          <BarChart data={rows}>
            <CartesianGrid stroke={GRID_STROKE} />
            <XAxis dataKey="group" stroke={INK} />
            <YAxis domain={[0.6, 'auto']} stroke={INK} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => (typeof v === 'number' ? v.toFixed(3) : v)} />
            <Legend />
            <Bar dataKey="rmse_knn_baseline" name="KNNBaseline" fill={INK} isAnimationActive={false} />
            <Bar dataKey="rmse_bias_only" name="Bias only" fill={MUTED} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

export function DsEvaluation() {
  const [split, setSplit] = useState<'test' | 'validation'>('test')
  const cmp = useQuery({ queryKey: ['ds-cmp'], queryFn: () => get<Comparison>('/ds/evaluation/comparison') })
  const tune = useQuery({ queryKey: ['ds-tune'], queryFn: () => get<{ items: TuningRow[] }>('/ds/evaluation/tuning') })
  const err = useQuery({ queryKey: ['ds-err'], queryFn: () => get<ErrorAnalysis>('/ds/evaluation/errors') })

  const thr = cmp.data?.config.serving.min_item_ratings ?? 0
  const rows = (cmp.data?.rows.filter((r) => r.split === split) ?? []).map((r) => ({ ...r, label: labelOf(r) }))

  // Tuning curves: other hyperparameters held at the best configuration; K and shrinkage vary.
  let curves: Record<string, number | string>[] = []
  let shrinks: number[] = []
  if (tune.data) {
    const t = tune.data.items
    const best = [...t].sort((a, b) => (a.val_rmse ?? 9) - (b.val_rmse ?? 9))[0]
    if (best) {
      const sub = t.filter((r) => r.reg_u === best.reg_u && r.reg_i === best.reg_i && r.min_support === best.min_support && r.min_k === best.min_k)
      shrinks = [...new Set(sub.map((r) => r.shrinkage as number))].sort((a, b) => a - b)
      curves = [...new Set(sub.map((r) => r.k as number))].sort((a, b) => a - b).map((k) => {
        const o: Record<string, number | string> = { k }
        for (const s of shrinks) o[`s${s}`] = sub.find((r) => r.k === k && r.shrinkage === s)?.val_rmse ?? NaN
        return o
      })
    }
  }

  return (
    <div className="space-y-8">
      <PageTitle title="Evaluation" subtitle="Five models compared on the same split, the same candidate set and the same fallback rules." />

      <Card title="Comparison table">
        <div className="mb-4 flex flex-wrap gap-0" role="tablist">
          {(['test', 'validation'] as const).map((s) => (
            <button key={s} role="tab" aria-selected={split === s} onClick={() => setSplit(s)} className={`btn -ml-0.5 first:ml-0 ${split === s ? 'btn-solid' : ''}`}>
              {s === 'test' ? 'Test (final)' : 'Validation (used for tuning)'}
            </button>
          ))}
        </div>
        {cmp.isLoading && <Spinner />}
        {cmp.error && <ErrorState error={cmp.error} retry={() => cmp.refetch()} />}
        {cmp.data && <CompareTable rows={rows} thr={thr} />}
      </Card>

      {cmp.data && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card title={`RMSE (${split}), lower is better`}>
            <div className="h-60">
              <ResponsiveContainer>
                <BarChart data={rows} layout="vertical" margin={{ left: 100 }}>
                  <CartesianGrid stroke={GRID_STROKE} />
                  <XAxis type="number" domain={[0.8, 1.1]} ticks={[0.8, 0.9, 1.0, 1.1]} stroke={INK} />
                  <YAxis type="category" dataKey="label" width={190} stroke={INK} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => (typeof v === 'number' ? v.toFixed(4) : v)} />
                  <Bar dataKey="rmse" fill={INK} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title={`NDCG@10 with >= ${thr} ratings (${split}), higher is better`}>
            <div className="h-60">
              <ResponsiveContainer>
                <BarChart data={rows} layout="vertical" margin={{ left: 100 }}>
                  <CartesianGrid stroke={GRID_STROKE} />
                  <XAxis type="number" stroke={INK} />
                  <YAxis type="category" dataKey="label" width={190} stroke={INK} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => (typeof v === 'number' ? v.toFixed(4) : v)} />
                  <Bar dataKey={`ndcg@10_min${thr}`} fill={ALERT} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      )}

      <Card title="Tuning on validation: RMSE by K and shrinkage">
        {tune.isLoading && <Spinner />}
        {tune.error && <ErrorState error={tune.error} retry={() => tune.refetch()} />}
        {curves.length > 0 && (
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={curves}>
                <CartesianGrid stroke={GRID_STROKE} />
                <XAxis dataKey="k" stroke={INK} label={{ value: 'K', position: 'insideBottom', offset: -2 }} />
                <YAxis domain={['auto', 'auto']} stroke={INK} />
                <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => (typeof v === 'number' ? v.toFixed(4) : v)} />
                <Legend />
                {shrinks.map((s, i) => (
                  <Line key={s} type="linear" isAnimationActive={false} connectNulls dataKey={`s${s}`} name={`shrinkage=${s}`} stroke={SERIES[i % SERIES.length].stroke} strokeDasharray={SERIES[i % SERIES.length].dash} strokeWidth={2} dot={{ r: 3, strokeWidth: 0, fill: SERIES[i % SERIES.length].stroke }} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
        <p className="micro mt-3 opacity-70">
          Other hyperparameters are held at the best configuration. Note: the chosen configuration sits on the edge of the grid (largest shrinkage) and the surface is very flat, so neighbouring configurations differ very little.
        </p>
      </Card>

      {err.isLoading && <Spinner />}
      {err.error && <ErrorState error={err.error} retry={() => err.refetch()} />}
      {err.data && (
        <>
          <h2 className="h-sec">Error analysis (test, KNNBaseline vs bias only)</h2>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <GroupChart title="By user activity" rows={err.data.by_user_activity} />
            <GroupChart title="By film popularity (train ratings)" rows={err.data.by_item_popularity} />
            <GroupChart title="By true rating" rows={err.data.by_true_rating} />
          </div>
          <Card title="By number of neighbours actually used (KNNBaseline)">
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Neighbours</th>
                    <th>Pairs</th>
                    <th>RMSE</th>
                    <th>Signed error</th>
                  </tr>
                </thead>
                <tbody>
                  {err.data.by_n_neighbors.map((g) => (
                    <tr key={g.group} className="num">
                      <td className="font-bold">{g.group}</td>
                      <td>{g.n}</td>
                      <td>{f4(g.rmse_knn_baseline)}</td>
                      <td>{f4(g.bias_knn_baseline)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <Card title="Ten worst predictions">
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Film</th>
                    <th>True</th>
                    <th>Predicted</th>
                    <th>Source</th>
                    <th>Neighbours</th>
                    <th>Train ratings of film</th>
                  </tr>
                </thead>
                <tbody>
                  {err.data.worst_10.map((w, i) => (
                    <tr key={i} className="num">
                      <td className="font-bold">{w.movie}</td>
                      <td>{w.rating}</td>
                      <td>{w.est.toFixed(2)}</td>
                      <td>{w.source}</td>
                      <td>{w.n_neighbors}</td>
                      <td>{w.item_train_n}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      <Card title="Limitations to keep in mind">
        <ul className="list-disc space-y-2 pl-5">
          <li>MovieLens 100K was collected in 1997-98 and the catalog is old. A random per-user split measures how well hidden tastes can be recovered, not how well the future can be predicted.</li>
          <li>Held-out films skew toward heavily rated titles (popularity bias), so the popular-films baseline is very strong on ranking metrics. The small gap between KNNBaseline and popular films has no confidence interval.</li>
          <li>The minimum-ratings threshold was chosen on validation while keeping at least 25% of the catalog as candidates. The test set was evaluated twice (before and after the threshold was added).</li>
          <li>An unrated film is not necessarily disliked, and offline evaluation is no substitute for testing with real users.</li>
        </ul>
      </Card>
    </div>
  )
}
