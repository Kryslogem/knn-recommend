import { Link } from 'react-router-dom'
import { useRating } from '../api/hooks'
import type { Movie } from '../api/types'
import { StarRating } from './StarRating'
import { useToast, errText } from './ui'

export function MovieCard({ movie, children }: { movie: Movie; children?: React.ReactNode }) {
  const { rate, clear } = useRating()
  const toast = useToast()
  const pending = rate.isPending ? rate.variables?.rating : undefined
  // Cập nhật lạc quan: hiện ngay điểm vừa bấm, tự quay về giá trị server nếu lỗi.
  const value = pending ?? movie.my_rating
  return (
    <article className="flex flex-col justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div>
        <Link to={`/movies/${movie.id}`} className="font-semibold text-slate-900 hover:text-indigo-700">
          {movie.title}
        </Link>
        <p className="mt-1 text-xs text-slate-500">{movie.genres.join(' · ') || 'Chưa phân loại'}</p>
        {movie.avg_rating_train != null && (
          <p className="mt-1 text-xs text-slate-500">
            TB {movie.avg_rating_train.toFixed(2)} ★ · {movie.n_ratings_train} lượt chấm
          </p>
        )}
        {children}
      </div>
      <div className="mt-3">
        <StarRating
          size="sm"
          value={value}
          disabled={rate.isPending || clear.isPending}
          onChange={(rating) => rate.mutate({ movieId: movie.id, rating }, { onError: (e) => toast('err', errText(e)) })}
          onClear={() => clear.mutate(movie.id, { onError: (e) => toast('err', errText(e)) })}
        />
      </div>
    </article>
  )
}
