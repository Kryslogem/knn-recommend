import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useRating } from '../api/hooks'
import { get } from '../api/client'
import type { Movie, Prediction } from '../api/types'
import { ExplainDrawer } from '../components/ExplainDrawer'
import { StarRating } from '../components/StarRating'
import { Button, Card, ErrorState, Skeleton, SourceBadge, errText, useToast } from '../components/ui'

export function MovieDetailPage() {
  const id = Number(useParams().id)
  const [open, setOpen] = useState(false)
  const toast = useToast()
  const { rate, clear } = useRating()
  const movie = useQuery({ queryKey: ['movie', id], queryFn: () => get<Movie>(`/movies/${id}`), enabled: Number.isInteger(id) })
  const pred = useQuery({ queryKey: ['prediction', id], queryFn: () => get<Prediction>(`/movies/${id}/prediction`), enabled: Number.isInteger(id) })

  if (movie.isLoading) return <Skeleton className="h-64" />
  if (movie.error) return <ErrorState error={movie.error} retry={() => movie.refetch()} />
  const m = movie.data!
  const value = rate.isPending ? rate.variables?.rating : m.my_rating
  const item = pred.data?.item

  return (
    <div className="space-y-4">
      <Link to="/movies" className="text-sm text-indigo-700 underline">
        ← Danh mục
      </Link>
      <Card>
        <h1 className="text-2xl font-bold">{m.title}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {m.genres.join(' · ')} {m.release_date && `· Phát hành ${m.release_date}`}
        </p>
        <p className="mt-2 text-sm text-slate-600">
          {m.avg_rating_train != null ? (
            <>
              Điểm trung bình <b>{m.avg_rating_train.toFixed(2)}</b> ★ từ {m.n_ratings_train} lượt chấm (dữ liệu MovieLens)
            </>
          ) : (
            'Phim này chưa có trong dữ liệu huấn luyện của mô hình.'
          )}
        </p>
        <div className="mt-4">
          <p className="mb-1 text-sm font-medium">Điểm của bạn</p>
          <StarRating
            value={value}
            disabled={rate.isPending || clear.isPending}
            onChange={(rating) => rate.mutate({ movieId: id, rating }, { onError: (e) => toast('err', errText(e)) })}
            onClear={() => clear.mutate(id, { onError: (e) => toast('err', errText(e)) })}
          />
        </div>
      </Card>

      <Card title="Điểm dự đoán cho bạn">
        {pred.isLoading && <Skeleton className="h-10" />}
        {pred.error && <ErrorState error={pred.error} retry={() => pred.refetch()} />}
        {pred.data && !item && <p className="text-sm text-slate-500">{pred.data.message ?? 'Chưa có dự đoán cho phim này.'}</p>}
        {item && (
          <div className="flex flex-wrap items-center gap-4">
            <span className="text-3xl font-bold text-indigo-700">{item.predicted_rating.toFixed(2)}</span>
            <SourceBadge source={item.source} />
            <Button variant="ghost" onClick={() => setOpen(true)}>
              Vì sao?
            </Button>
            {pred.data!.profile_size === 0 && <span className="text-sm text-slate-500">Chấm vài phim để có dự đoán cá nhân hóa.</span>}
          </div>
        )}
        <p className="mt-2 text-xs text-slate-500">Điểm dự đoán không phải xác suất bạn sẽ thích phim.</p>
      </Card>
      {open && item && <ExplainDrawer item={item} onClose={() => setOpen(false)} />}
    </div>
  )
}
