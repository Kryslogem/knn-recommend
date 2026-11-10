import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { get, qs } from '../api/client'
import type { RecItem, Recommendations } from '../api/types'
import { ExplainDrawer } from '../components/ExplainDrawer'
import { PageTitle } from '../components/Layout'
import { MovieCard } from '../components/MovieCard'
import { Button, EmptyState, ErrorState, SkeletonGrid, SourceBadge } from '../components/ui'

export function RecommendationsPage() {
  const [genre, setGenre] = useState('')
  const [n, setN] = useState(10)
  const [explain, setExplain] = useState<RecItem | null>(null)
  const genres = useQuery({ queryKey: ['genres'], queryFn: () => get<{ items: string[] }>('/genres'), staleTime: Infinity })
  const q = useQuery({
    queryKey: ['recs', 'page', genre, n],
    queryFn: () => get<Recommendations>(`/recommendations${qs({ n, genre })}`),
    placeholderData: keepPreviousData,
  })
  const d = q.data
  const input = 'rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm'

  return (
    <div>
      <PageTitle title="Đề xuất cho bạn" subtitle="Được tính trực tiếp từ các điểm bạn đã chấm, so với những người có gu giống bạn." />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select className={input} aria-label="Thể loại" value={genre} onChange={(e) => setGenre(e.target.value)}>
          <option value="">Mọi thể loại</option>
          {genres.data?.items.map((g) => (
            <option key={g}>{g}</option>
          ))}
        </select>
        <select className={input} aria-label="Số phim" value={n} onChange={(e) => setN(Number(e.target.value))}>
          {[5, 10, 20, 50].map((x) => (
            <option key={x} value={x}>
              {x} phim
            </option>
          ))}
        </select>
        {d && (
          <span className="text-xs text-slate-500">
            Dựa trên {d.profile_size} phim bạn đã chấm · mô hình <code>{d.model_version}</code> · {d.latency_ms} ms{d.cached ? ' (từ bộ nhớ đệm)' : ''}
          </span>
        )}
      </div>

      {q.isLoading && <SkeletonGrid n={6} />}
      {q.error && <ErrorState error={q.error} retry={() => q.refetch()} />}

      {d && d.profile_size === 0 && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          Bạn chưa chấm phim nào nên đây chỉ là phim phổ biến. <Link to="/onboarding" className="font-medium underline">Chấm vài phim</Link> để nhận đề xuất cá nhân hóa.
        </div>
      )}
      {d?.message && d.profile_size > 0 && <p className="mb-3 rounded bg-amber-50 p-3 text-sm text-amber-900">{d.message}</p>}
      {d && d.items.length === 0 && <EmptyState title="Không có đề xuất phù hợp">Thử đổi thể loại hoặc chấm thêm phim.</EmptyState>}

      {d && d.items.length > 0 && (
        <>
          <p className="mb-3 text-xs text-slate-500">
            Phim có ít hơn {d.min_item_ratings} lượt chấm trong dữ liệu huấn luyện không được đưa vào danh sách để tránh đề xuất phim quá hiếm. Điểm dự đoán không phải xác suất bạn sẽ thích.
          </p>
          <ol className={`grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 ${q.isPlaceholderData ? 'opacity-60' : ''}`}>
            {d.items.map((it, i) => (
              <li key={it.movie.id}>
                <MovieCard movie={it.movie}>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                    <span className="text-xs text-slate-400">#{i + 1}</span>
                    <b className="text-lg text-indigo-700">{it.predicted_rating.toFixed(2)}</b>
                    <SourceBadge source={it.source} />
                    {it.source === 'knn' && <span className="text-xs text-slate-500">{it.n_neighbors} người giống bạn</span>}
                    <Button variant="ghost" className="ml-auto !px-2 !py-0.5 text-xs" onClick={() => setExplain(it)}>
                      Vì sao?
                    </Button>
                  </div>
                </MovieCard>
              </li>
            ))}
          </ol>
        </>
      )}
      {explain && <ExplainDrawer item={explain} onClose={() => setExplain(null)} />}
    </div>
  )
}
