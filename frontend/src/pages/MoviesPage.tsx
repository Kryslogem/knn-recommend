import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { get, qs } from '../api/client'
import type { Movie, Page } from '../api/types'
import { PageTitle } from '../components/Layout'
import { MovieCard } from '../components/MovieCard'
import { EmptyState, ErrorState, Pagination, SkeletonGrid, useDebounce } from '../components/ui'

const SORTS = [
  ['title', 'Title A-Z'],
  ['popular', 'Most rated'],
  ['year_desc', 'Newest'],
  ['year_asc', 'Oldest'],
] as const

export function MoviesPage() {
  const [q, setQ] = useState('')
  const [genre, setGenre] = useState('')
  const [yearFrom, setYearFrom] = useState('')
  const [yearTo, setYearTo] = useState('')
  const [sort, setSort] = useState<(typeof SORTS)[number][0]>('title')
  const [page, setPage] = useState(1)
  const dq = useDebounce(q.trim())
  const genres = useQuery({ queryKey: ['genres'], queryFn: () => get<{ items: string[] }>('/genres'), staleTime: Infinity })

  const yf = yearFrom ? Number(yearFrom) : undefined
  const yt = yearTo ? Number(yearTo) : undefined
  const badYear = [yf, yt].some((y) => y !== undefined && (!Number.isInteger(y) || y < 1800 || y > 2100)) || (yf !== undefined && yt !== undefined && yf > yt)
  const params = { q: dq, genre, year_from: yf, year_to: yt, sort, page, page_size: 20 }
  const list = useQuery({
    queryKey: ['movies', params],
    queryFn: () => get<Page<Movie>>(`/movies${qs(params)}`),
    placeholderData: keepPreviousData,
    enabled: !badYear,
  })
  const reset = <T,>(set: (v: T) => void) => (v: T) => {
    set(v)
    setPage(1)
  }

  return (
    <div>
      <PageTitle title="Catalog" subtitle="Search by title, filter by genre or year, and rate directly on the card." />
      <div className="mb-6 grid grid-cols-2 gap-3 border-2 border-ink p-3 md:grid-cols-[2fr_1.2fr_0.7fr_0.7fr_1fr]">
        <input className="field col-span-2 md:col-span-1" placeholder="Search title…" aria-label="Search by title" value={q} onChange={(e) => reset(setQ)(e.target.value)} />
        <select className="field" aria-label="Genre" value={genre} onChange={(e) => reset(setGenre)(e.target.value)}>
          <option value="">All genres</option>
          {genres.data?.items.map((g) => (
            <option key={g}>{g}</option>
          ))}
        </select>
        <input className="field" placeholder="From year" aria-label="From year" inputMode="numeric" value={yearFrom} onChange={(e) => reset(setYearFrom)(e.target.value.replace(/\D/g, ''))} />
        <input className="field" placeholder="To year" aria-label="To year" inputMode="numeric" value={yearTo} onChange={(e) => reset(setYearTo)(e.target.value.replace(/\D/g, ''))} />
        <select className="field" aria-label="Sort order" value={sort} onChange={(e) => reset(setSort)(e.target.value as typeof sort)}>
          {SORTS.map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
      </div>
      {badYear && <p className="mb-3 font-bold text-alert">/// Invalid year range (1800-2100, and "from" must not exceed "to").</p>}
      {list.isLoading && <SkeletonGrid />}
      {list.error && <ErrorState error={list.error} retry={() => list.refetch()} />}
      {list.data && list.data.items.length === 0 && (
        <EmptyState title="No films match">Try removing a filter or changing the search term.</EmptyState>
      )}
      {list.data && list.data.items.length > 0 && (
        <>
          <div className={`ruled grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 ${list.isPlaceholderData ? 'opacity-60' : ''}`}>
            {list.data.items.map((m) => (
              <MovieCard key={m.id} movie={m} />
            ))}
          </div>
          <Pagination page={list.data.page} pageSize={list.data.page_size} total={list.data.total} onChange={setPage} />
        </>
      )}
    </div>
  )
}
