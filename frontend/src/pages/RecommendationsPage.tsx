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

  return (
    <div>
      <PageTitle title="For you" subtitle="Computed live from your own ratings, by comparing you with viewers who share your taste." />
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <select className="field !w-auto" aria-label="Genre" value={genre} onChange={(e) => setGenre(e.target.value)}>
          <option value="">All genres</option>
          {genres.data?.items.map((g) => (
            <option key={g}>{g}</option>
          ))}
        </select>
        <select className="field !w-auto" aria-label="Number of films" value={n} onChange={(e) => setN(Number(e.target.value))}>
          {[5, 10, 20, 50].map((x) => (
            <option key={x} value={x}>
              {x} films
            </option>
          ))}
        </select>
        {d && (
          <span className="micro num">
            From {d.profile_size} rated · model {d.model_version} · {d.latency_ms} ms{d.cached ? ' · cached' : ''}
          </span>
        )}
      </div>

      {q.isLoading && <SkeletonGrid n={6} />}
      {q.error && <ErrorState error={q.error} retry={() => q.refetch()} />}

      {d && d.profile_size === 0 && (
        <div className="mb-6 border-2 border-ink bg-paper-2 p-4">
          <b>/// You have not rated anything yet, so these are just popular films.</b>{' '}
          <Link to="/onboarding" className="underline hover:text-alert">
            Rate a few films
          </Link>{' '}
          to get personalized recommendations.
        </div>
      )}
      {d?.message && d.profile_size > 0 && <p className="mb-4 border-2 border-alert p-3 font-bold">/// {d.message}</p>}
      {d && d.items.length === 0 && <EmptyState title="No recommendations to show">Try another genre, or rate more films.</EmptyState>}

      {d && d.items.length > 0 && (
        <>
          <p className="micro mb-4 max-w-4xl leading-relaxed opacity-80">
            Films with fewer than {d.min_item_ratings} ratings in the training data are left out so the list does not fill up with very obscure titles. A predicted rating is not the probability that you will like the film.
          </p>
          <ol className={`ruled grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 ${q.isPlaceholderData ? 'opacity-60' : ''}`}>
            {d.items.map((it, i) => (
              <li key={it.movie.id}>
                <MovieCard movie={it.movie}>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span className="display num text-sm opacity-50">#{String(i + 1).padStart(2, '0')}</span>
                    <b className="display num text-3xl">{it.predicted_rating.toFixed(2)}</b>
                    <SourceBadge source={it.source} />
                    {it.source === 'knn' && <span className="micro">{it.n_neighbors} similar viewers</span>}
                  </div>
                  <div className="mt-3">
                    <Button variant="ghost" className="btn-sm" onClick={() => setExplain(it)}>
                      Why? &gt;&gt;&gt;
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
