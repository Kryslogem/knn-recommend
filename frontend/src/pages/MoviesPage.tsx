import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { get, qs } from '../api/client'
import type { Movie, Page } from '../api/types'
import { MovieCard } from '../components/MovieCard'
import { PageTitle } from '../components/Layout'
import { EmptyState, ErrorState, Pagination, SkeletonGrid, useDebounce } from '../components/ui'

const SORTS = [
  ['title', 'Tên A–Z'],
  ['popular', 'Phổ biến nhất'],
  ['year_desc', 'Mới nhất'],
  ['year_asc', 'Cũ nhất'],
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

  const input = 'rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm'
  return (
    <div>
      <PageTitle title="Danh mục phim" subtitle="Tìm phim theo tên, lọc theo thể loại hoặc năm rồi chấm điểm ngay trên thẻ." />
      <div className="mb-4 flex flex-wrap gap-3">
        <input className={`${input} w-64`} placeholder="Tìm theo tên phim…" aria-label="Tìm theo tên phim" value={q} onChange={(e) => reset(setQ)(e.target.value)} />
        <select className={input} aria-label="Thể loại" value={genre} onChange={(e) => reset(setGenre)(e.target.value)}>
          <option value="">Mọi thể loại</option>
          {genres.data?.items.map((g) => (
            <option key={g}>{g}</option>
          ))}
        </select>
        <input className={`${input} w-24`} placeholder="Từ năm" aria-label="Từ năm" inputMode="numeric" value={yearFrom} onChange={(e) => reset(setYearFrom)(e.target.value.replace(/\D/g, ''))} />
        <input className={`${input} w-24`} placeholder="Đến năm" aria-label="Đến năm" inputMode="numeric" value={yearTo} onChange={(e) => reset(setYearTo)(e.target.value.replace(/\D/g, ''))} />
        <select className={input} aria-label="Sắp xếp" value={sort} onChange={(e) => reset(setSort)(e.target.value as typeof sort)}>
          {SORTS.map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
      </div>
      {badYear && <p className="mb-3 text-sm text-red-600">Khoảng năm không hợp lệ (1800–2100, “từ” không lớn hơn “đến”).</p>}
      {list.isLoading && <SkeletonGrid />}
      {list.error && <ErrorState error={list.error} retry={() => list.refetch()} />}
      {list.data && list.data.items.length === 0 && <EmptyState title="Không có phim phù hợp">Thử bỏ bớt bộ lọc hoặc đổi từ khóa.</EmptyState>}
      {list.data && list.data.items.length > 0 && (
        <>
          <div className={`grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 ${list.isPlaceholderData ? 'opacity-60' : ''}`}>
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
