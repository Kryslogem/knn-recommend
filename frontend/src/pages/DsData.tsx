import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { get } from '../api/client'
import type { DataReport, SplitManifest } from '../api/types'
import { PageTitle } from '../components/Layout'
import { Card, ErrorState, Spinner, Stat } from '../components/ui'

const fmt = (n: number) => n.toLocaleString('vi-VN')

export function DsOverview() {
  const report = useQuery({ queryKey: ['ds-report'], queryFn: () => get<DataReport>('/ds/data/report') })
  const split = useQuery({ queryKey: ['ds-split'], queryFn: () => get<SplitManifest>('/ds/data/split') })

  if (report.isLoading) return <Spinner />
  if (report.error) return <ErrorState error={report.error} retry={() => report.refetch()} />
  const r = report.data!
  const s = r.stats
  const dist = Object.entries(s.rating_distribution).map(([k, v]) => ({ rating: `${k}★`, count: v }))
  const genres = Object.entries(s.genre_counts).map(([k, v]) => ({ genre: k, count: v })).sort((a, b) => b.count - a.count)

  return (
    <div className="space-y-6">
      <PageTitle title="Dữ liệu và chia tập" subtitle={`Nguồn: ${r.source.name} — báo cáo sinh lúc ${r.generated_at.replace('T', ' ').slice(0, 19)} UTC`} />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Người dùng" value={fmt(s.n_users)} />
        <Stat label="Phim" value={fmt(s.n_items_catalog)} hint={`${s.items_with_lt_5_ratings} phim có < 5 rating`} />
        <Stat label="Lượt đánh giá" value={fmt(s.n_ratings)} hint={`TB ${s.rating_mean}★`} />
        <Stat label="Độ thưa" value={`${(s.sparsity * 100).toFixed(2)}%`} />
      </div>

      <Card title="Nguồn và toàn vẹn">
        <dl className="space-y-1 text-sm">
          <div><dt className="inline text-slate-500">URL: </dt><dd className="inline break-all">{r.source.url}</dd></div>
          <div><dt className="inline text-slate-500">SHA-256 (zip): </dt><dd className="inline break-all font-mono text-xs">{r.source.zip_sha256}</dd> <span className={r.source.checksum_verified ? 'text-emerald-700' : 'text-amber-700'}>{r.source.checksum_verified ? '✓ đã đối chiếu cấu hình' : 'chưa đối chiếu'}</span></div>
          <div><dt className="inline text-slate-500">Làm sạch: </dt><dd className="inline">bỏ {r.cleaning.duplicate_rows_dropped} dòng trùng, còn {fmt(r.cleaning.rows_after_cleaning)} dòng</dd></div>
          <div><dt className="inline text-slate-500">Thời gian thu thập: </dt><dd className="inline">{r.stats.timestamp_range_utc.map((t) => t.slice(0, 10)).join(' → ')}</dd></div>
        </dl>
      </Card>

      <Card title={`Kiểm tra chất lượng dữ liệu — ${r.ok ? 'đạt' : 'CÓ LỖI'}`}>
        <ul className="grid grid-cols-1 gap-1 text-sm sm:grid-cols-2">
          {r.checks.map((c) => (
            <li key={c.name} className="flex items-center gap-2">
              <span className={c.passed ? 'text-emerald-600' : c.severity === 'error' ? 'text-red-600' : 'text-amber-600'} aria-label={c.passed ? 'đạt' : c.severity === 'error' ? 'lỗi' : 'cảnh báo'}>
                {c.passed ? '✔' : c.severity === 'error' ? '✘' : '⚠'}
              </span>
              <code className="text-xs">{c.name}</code>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-slate-500">Cảnh báo không chặn pipeline (vd. tên phim trùng nhưng movie_id khác nhau).</p>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Phân bố rating">
          <div className="h-56"><ResponsiveContainer><BarChart data={dist}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="rating" /><YAxis /><Tooltip /><Bar dataKey="count" fill="#4f46e5" name="Số lượt" /></BarChart></ResponsiveContainer></div>
        </Card>
        <Card title="Số phim theo thể loại">
          <div className="h-56"><ResponsiveContainer><BarChart data={genres}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="genre" angle={-45} textAnchor="end" interval={0} height={70} tick={{ fontSize: 10 }} /><YAxis /><Tooltip /><Bar dataKey="count" fill="#0891b2" name="Số phim" /></BarChart></ResponsiveContainer></div>
        </Card>
      </div>

      <Card title="Phân bố số rating (toàn bộ dữ liệu)">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase text-slate-500"><tr><th>Đối tượng</th><th>Min</th><th>P25</th><th>Trung vị</th><th>TB</th><th>P75</th><th>Max</th></tr></thead>
          <tbody>
            {([['Mỗi người dùng', s.ratings_per_user], ['Mỗi phim', s.ratings_per_item]] as const).map(([name, d]) => (
              <tr key={name} className="border-t border-slate-100"><td className="py-1">{name}</td><td>{d.min}</td><td>{d.p25}</td><td>{d.median}</td><td>{d.mean}</td><td>{d.p75}</td><td>{d.max}</td></tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="Chia tập (chống rò rỉ)">
        {split.isLoading && <Spinner />}
        {split.error && <ErrorState error={split.error} />}
        {split.data && (
          <div className="space-y-3 text-sm">
            <p>
              Chiến lược <b>{split.data.strategy}</b>, seed <b>{split.data.seed}</b>, tỉ lệ{' '}
              {Object.entries(split.data.fractions).map(([k, v]) => `${k} ${v * 100}%`).join(' / ')}. Làm tròn: <span className="text-slate-600">{split.data.rounding}</span>.
            </p>
            <table className="w-full text-left">
              <thead className="text-xs uppercase text-slate-500"><tr><th>Tập</th><th>Số dòng</th><th>Phim không có trong train</th></tr></thead>
              <tbody>
                {Object.entries(split.data.summary.rows).map(([k, v]) => (
                  <tr key={k} className="border-t border-slate-100">
                    <td className="py-1">{k}</td><td>{fmt(v)}</td>
                    <td>{k === 'train' ? '—' : `${(split.data!.summary as Record<string, unknown>)[`${k}_items_not_in_train`] ?? '—'} phim (${(split.data!.summary as Record<string, unknown>)[`${k}_rows_with_item_not_in_train`] ?? '—'} dòng, dùng fallback)`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="break-all text-xs text-slate-500">split_hash: <code>{split.data.split_hash}</code></p>
          </div>
        )}
      </Card>
    </div>
  )
}
