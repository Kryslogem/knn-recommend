import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { get, qs } from '../api/client'
import { useRating } from '../api/hooks'
import type { HistoryItem, Page } from '../api/types'
import { PageTitle } from '../components/Layout'
import { StarRating } from '../components/StarRating'
import { EmptyState, ErrorState, Pagination, Skeleton, errText, useToast } from '../components/ui'

function Row({ it }: { it: HistoryItem }) {
  const { rate, clear } = useRating()
  const toast = useToast()
  const value = rate.isPending ? rate.variables?.rating : it.rating
  return (
    <tr className="border-t border-slate-100">
      <td className="py-2 pr-3">
        <Link to={`/movies/${it.movie.id}`} className="font-medium text-slate-900 hover:text-indigo-700">
          {it.movie.title}
        </Link>
        <div className="text-xs text-slate-500">{it.movie.genres.join(' · ')}</div>
      </td>
      <td className="py-2 pr-3">
        <StarRating
          size="sm"
          value={value}
          disabled={rate.isPending || clear.isPending}
          onChange={(rating) => rate.mutate({ movieId: it.movie.id, rating }, { onError: (e) => toast('err', errText(e)) })}
          onClear={() => clear.mutate(it.movie.id, { onError: (e) => toast('err', errText(e)), onSuccess: () => toast('ok', 'Đã xóa điểm') })}
        />
      </td>
      <td className="py-2 text-xs text-slate-500">{new Date(it.updated_at + 'Z').toLocaleString('vi-VN')}</td>
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
      <PageTitle title="Lịch sử đánh giá" subtitle="Sửa hoặc xóa điểm ở đây; đề xuất sẽ được tính lại ngay." />
      <select
        className="mb-4 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm"
        aria-label="Sắp xếp"
        value={sort}
        onChange={(e) => {
          setSort(e.target.value)
          setPage(1)
        }}
      >
        <option value="recent">Mới chấm gần đây</option>
        <option value="rating_desc">Điểm cao → thấp</option>
        <option value="rating_asc">Điểm thấp → cao</option>
        <option value="title">Tên A–Z</option>
      </select>
      {q.isLoading && <Skeleton className="h-40" />}
      {q.error && <ErrorState error={q.error} retry={() => q.refetch()} />}
      {q.data && q.data.total === 0 && (
        <EmptyState title="Bạn chưa chấm phim nào">
          <Link to="/onboarding" className="text-indigo-700 underline">Bắt đầu chấm điểm</Link>
        </EmptyState>
      )}
      {q.data && q.data.total > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white p-4">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="pb-2">Phim</th>
                  <th className="pb-2">Điểm của bạn</th>
                  <th className="pb-2">Cập nhật</th>
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
