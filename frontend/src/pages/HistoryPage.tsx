import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { get, qs } from '../api/client'
import { useRating } from '../api/hooks'
import type { HistoryItem, Page } from '../api/types'
import { PageTitle } from '../components/Layout'
import { RatingInput } from '../components/RatingInput'
import { EmptyState, ErrorState, Pagination, Skeleton, errText, useToast } from '../components/ui'

function Row({ it }: { it: HistoryItem }) {
  const { rate, clear } = useRating()
  const toast = useToast()
  const value = rate.isPending ? rate.variables?.rating : it.rating
  return (
    <tr>
      <td>
        <Link to={`/movies/${it.movie.id}`} className="display text-base tracking-[-0.02em] hover:text-alert">
          {it.movie.title}
        </Link>
        <div className="micro mt-1">{it.movie.genres.join(' / ')}</div>
      </td>
      <td>
        <RatingInput
          size="sm"
          value={value}
          disabled={rate.isPending || clear.isPending}
          onChange={(rating) => rate.mutate({ movieId: it.movie.id, rating }, { onError: (e) => toast('err', errText(e)) })}
          onClear={() => clear.mutate(it.movie.id, { onError: (e) => toast('err', errText(e)), onSuccess: () => toast('ok', 'Rating removed') })}
        />
      </td>
      <td className="micro num">{new Date(it.updated_at + 'Z').toLocaleString('en-GB')}</td>
    </tr>
  )
}

export function HistoryPage() {
  const [sort, setSort] = useState('recent')
  const [page, setPage] = useState(1)
  const q = useQuery({
    queryKey: ['history', sort, page],
    queryFn: () => get<Page<HistoryItem>>(`/ratings/me${qs({ sort, page, page_size: 20 })}`),
    placeholderData: keepPreviousData,
  })
  return (
    <div>
      <PageTitle title="My ratings" subtitle="Edit or remove a rating here. Your recommendations are recomputed immediately." />
      <select
        className="field mb-6 !w-auto"
        aria-label="Sort order"
        value={sort}
        onChange={(e) => {
          setSort(e.target.value)
          setPage(1)
        }}
      >
        <option value="recent">Recently rated</option>
        <option value="rating_desc">Highest first</option>
        <option value="rating_asc">Lowest first</option>
        <option value="title">Title A-Z</option>
      </select>
      {q.isLoading && <Skeleton className="h-40" />}
      {q.error && <ErrorState error={q.error} retry={() => q.refetch()} />}
      {q.data && q.data.total === 0 && (
        <EmptyState title="You have not rated any film">
          <Link to="/onboarding" className="underline hover:text-alert">
            Start rating &gt;&gt;&gt;
          </Link>
        </EmptyState>
      )}
      {q.data && q.data.total > 0 && (
        <>
          <div className="panel overflow-x-auto p-2">
            <table className="table">
              <thead>
                <tr>
                  <th>Film</th>
                  <th>Your rating</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {q.data.items.map((it) => (
                  <Row key={it.movie.id} it={it} />
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={q.data.page} pageSize={q.data.page_size} total={q.data.total} onChange={setPage} />
        </>
      )}
    </div>
  )
}
