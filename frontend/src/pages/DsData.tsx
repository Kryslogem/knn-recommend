import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { get } from '../api/client'
import type { DataReport, SplitManifest } from '../api/types'
import { PageTitle } from '../components/Layout'
import { Card, ErrorState, Spinner, Stat } from '../components/ui'
import { GRID_STROKE, INK, TOOLTIP_STYLE } from './chartStyle'

const fmt = (n: number) => n.toLocaleString('en-US')

export function DsOverview() {
  const report = useQuery({ queryKey: ['ds-report'], queryFn: () => get<DataReport>('/ds/data/report') })
  const split = useQuery({ queryKey: ['ds-split'], queryFn: () => get<SplitManifest>('/ds/data/split') })

  if (report.isLoading) return <Spinner />
  if (report.error) return <ErrorState error={report.error} retry={() => report.refetch()} />
  const r = report.data!
  const s = r.stats
  const dist = Object.entries(s.rating_distribution).map(([k, v]) => ({ rating: `${k}`, count: v }))
  const genres = Object.entries(s.genre_counts).map(([k, v]) => ({ genre: k, count: v })).sort((a, b) => b.count - a.count)
  const sumRow = split.data?.summary as Record<string, unknown> | undefined

  return (
    <div className="space-y-8">
      <PageTitle title="Data and split" subtitle={`Source: ${r.source.name}. Report generated ${r.generated_at.replace('T', ' ').slice(0, 19)} UTC.`} />
      <div className="ruled grid-cols-2 lg:grid-cols-4">
        <Stat label="Users" value={fmt(s.n_users)} />
        <Stat label="Films" value={fmt(s.n_items_catalog)} hint={`${s.items_with_lt_5_ratings} films with fewer than 5 ratings`} />
        <Stat label="Ratings" value={fmt(s.n_ratings)} hint={`Mean ${s.rating_mean}`} />
        <Stat label="Sparsity" value={`${(s.sparsity * 100).toFixed(2)}%`} />
      </div>

      <Card title="Source and integrity">
        <dl className="space-y-2">
          <div>
            <dt className="micro opacity-70">URL</dt>
            <dd className="break-all">{r.source.url}</dd>
          </div>
          <div>
            <dt className="micro opacity-70">SHA-256 (zip)</dt>
            <dd className="break-all">
              {r.source.zip_sha256} <span className={`tag ml-1 ${r.source.checksum_verified ? 'tag-solid' : 'tag-alert'}`}>{r.source.checksum_verified ? 'Verified against config' : 'Not verified'}</span>
            </dd>
          </div>
          <div>
            <dt className="micro opacity-70">Cleaning</dt>
            <dd>
              {r.cleaning.duplicate_rows_dropped} duplicate rows dropped, {fmt(r.cleaning.rows_after_cleaning)} rows remain
            </dd>
          </div>
          <div>
            <dt className="micro opacity-70">Collected</dt>
            <dd>{r.stats.timestamp_range_utc.map((t) => t.slice(0, 10)).join(' to ')}</dd>
          </div>
        </dl>
      </Card>

      <Card title={`Data quality checks: ${r.ok ? 'all passed' : 'FAILURES'}`}>
        <ul className="ruled grid-cols-1 sm:grid-cols-2">
          {r.checks.map((c) => (
            <li key={c.name} className="flex items-center gap-3 px-3 py-2">
              <span className={`tag ${c.passed ? 'tag-solid' : c.severity === 'error' ? 'tag-alert' : ''}`}>{c.passed ? 'Pass' : c.severity === 'error' ? 'Fail' : 'Warn'}</span>
              <code>{c.name}</code>
            </li>
          ))}
        </ul>
        <p className="micro mt-3 opacity-70">Warnings do not stop the pipeline (for example, duplicate titles that have different movie IDs).</p>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Rating distribution">
          <div className="h-60">
            <ResponsiveContainer>
              <BarChart data={dist}>
                <CartesianGrid stroke={GRID_STROKE} />
                <XAxis dataKey="rating" stroke={INK} />
                <YAxis stroke={INK} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="count" name="Ratings" fill={INK} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Films per genre">
          <div className="h-60">
            <ResponsiveContainer>
              <BarChart data={genres}>
                <CartesianGrid stroke={GRID_STROKE} />
                <XAxis dataKey="genre" angle={-45} textAnchor="end" interval={0} height={70} stroke={INK} />
                <YAxis stroke={INK} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="count" name="Films" fill={INK} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card title="Ratings per user and per film (all data)">
        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Min</th>
                <th>P25</th>
                <th>Median</th>
                <th>Mean</th>
                <th>P75</th>
                <th>Max</th>
              </tr>
            </thead>
            <tbody>
              {([['Per user', s.ratings_per_user], ['Per film', s.ratings_per_item]] as const).map(([name, d]) => (
                <tr key={name} className="num">
                  <td className="font-bold">{name}</td>
                  <td>{d.min}</td>
                  <td>{d.p25}</td>
                  <td>{d.median}</td>
                  <td>{d.mean}</td>
                  <td>{d.p75}</td>
                  <td>{d.max}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Train / validation / test split (leakage control)">
        {split.isLoading && <Spinner />}
        {split.error && <ErrorState error={split.error} />}
        {split.data && sumRow && (
          <div className="space-y-4">
            <p>
              Strategy <b>{split.data.strategy}</b>, seed <b>{split.data.seed}</b>, fractions {Object.entries(split.data.fractions).map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(' / ')}. Rounding: <code>{split.data.rounding}</code>.
            </p>
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Set</th>
                    <th>Rows</th>
                    <th>Films not in train</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(split.data.summary.rows).map(([k, v]) => (
                    <tr key={k} className="num">
                      <td className="font-bold">{k}</td>
                      <td>{fmt(v)}</td>
                      <td>{k === 'train' ? '-' : `${sumRow[`${k}_items_not_in_train`] ?? '-'} films (${sumRow[`${k}_rows_with_item_not_in_train`] ?? '-'} rows, handled by fallback)`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="micro break-all opacity-70">split_hash: {split.data.split_hash}</p>
          </div>
        )}
      </Card>
    </div>
  )
}
