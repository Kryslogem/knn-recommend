import { useQuery } from '@tanstack/react-query'
import { Link, Navigate } from 'react-router-dom'
import { get } from '../api/client'
import type { Movie, Recommendations, User } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { MovieCard } from '../components/MovieCard'
import { PageTitle } from '../components/Layout'
import { Button, ErrorState, SkeletonGrid, SourceBadge } from '../components/ui'

export function PopularGrid({ n = 12 }: { n?: number }) {
  // staleTime vô hạn: danh sách không tự đổi khi người dùng đang chấm điểm ngay trên các thẻ.
  const q = useQuery({ queryKey: ['popular', n], queryFn: () => get<{ items: Movie[] }>(`/movies/popular?n=${n}`), staleTime: Infinity })
  if (q.isLoading) return <SkeletonGrid n={Math.min(n, 8)} />
  if (q.error) return <ErrorState error={q.error} retry={() => q.refetch()} />
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {q.data!.items.map((m) => (
        <MovieCard key={m.id} movie={m} />
      ))}
    </div>
  )
}

export function HomePage() {
  const { user } = useAuth()
  const me = useQuery({ queryKey: ['me'], queryFn: () => get<User>('/auth/me') })
  const hasProfile = (me.data?.n_ratings ?? user?.n_ratings ?? 0) > 0
  const recs = useQuery({
    queryKey: ['recs', 'home'],
    queryFn: () => get<Recommendations>('/recommendations?n=4'),
    enabled: hasProfile,
  })

  if (me.data && me.data.n_ratings === 0) return <Navigate to="/onboarding" replace />

  return (
    <div className="space-y-8">
      <PageTitle title={`Xin chào, ${user?.username}`} subtitle="Chấm điểm những phim bạn đã xem để nhận đề xuất phù hợp với gu của bạn." />

      {hasProfile && (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Đề xuất cho bạn</h2>
            <Link to="/recommendations" className="text-sm text-indigo-700 underline">
              Xem tất cả
            </Link>
          </div>
          {recs.isLoading && <SkeletonGrid n={4} />}
          {recs.error && <ErrorState error={recs.error} retry={() => recs.refetch()} />}
          {recs.data && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {recs.data.items.map((it) => (
                <MovieCard key={it.movie.id} movie={it.movie}>
                  <p className="mt-2 flex items-center gap-2 text-sm">
                    <b className="text-indigo-700">{it.predicted_rating.toFixed(2)}</b> dự đoán <SourceBadge source={it.source} />
                  </p>
                </MovieCard>
              ))}
            </div>
          )}
        </section>
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold">Phim phổ biến</h2>
        <PopularGrid n={8} />
        {!hasProfile && (
          <div className="mt-4">
            <Link to="/onboarding">
              <Button>Bắt đầu chấm điểm</Button>
            </Link>
          </div>
        )}
      </section>
    </div>
  )
}
