import { useQuery } from '@tanstack/react-query'
import { Link, Navigate } from 'react-router-dom'
import { get } from '../api/client'
import type { Movie, Recommendations, User } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { PageTitle } from '../components/Layout'
import { MovieCard } from '../components/MovieCard'
import { Button, ErrorState, SkeletonGrid, SourceBadge } from '../components/ui'

const GRID = 'ruled grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'

export function PopularGrid({ n = 12 }: { n?: number }) {
  // Infinite staleTime: the list must not reshuffle while the user is rating the cards in front of them.
  const q = useQuery({ queryKey: ['popular', n], queryFn: () => get<{ items: Movie[] }>(`/movies/popular?n=${n}`), staleTime: Infinity })
  if (q.isLoading) return <SkeletonGrid n={Math.min(n, 8)} />
  if (q.error) return <ErrorState error={q.error} retry={() => q.refetch()} />
  return (
    <div className={GRID}>
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
    <div className="space-y-12">
      <PageTitle title={`Hello, ${user?.username}`} subtitle="Rate the films you have seen to get recommendations that match your taste." />

      {hasProfile && (
        <section>
          <div className="mb-3 flex items-end justify-between gap-3">
            <h2 className="h-sec">Recommended for you</h2>
            <Link to="/recommendations" className="micro underline hover:text-alert">
              See all &gt;&gt;&gt;
            </Link>
          </div>
          {recs.isLoading && <SkeletonGrid n={4} />}
          {recs.error && <ErrorState error={recs.error} retry={() => recs.refetch()} />}
          {recs.data && (
            <div className="ruled grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
              {recs.data.items.map((it) => (
                <MovieCard key={it.movie.id} movie={it.movie}>
                  <p className="mt-3 flex items-center gap-2">
                    <b className="display num text-2xl">{it.predicted_rating.toFixed(2)}</b>
                    <span className="micro">predicted</span> <SourceBadge source={it.source} />
                  </p>
                </MovieCard>
              ))}
            </div>
          )}
        </section>
      )}

      <section>
        <h2 className="h-sec mb-3">Popular films</h2>
        <PopularGrid n={8} />
        {!hasProfile && (
          <div className="mt-4">
            <Link to="/onboarding">
              <Button>Start rating &gt;&gt;&gt;</Button>
            </Link>
          </div>
        )}
      </section>
    </div>
  )
}
