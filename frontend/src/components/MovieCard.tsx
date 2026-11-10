import { Link } from 'react-router-dom'
import { useRating } from '../api/hooks'
import type { Movie } from '../api/types'
import { RatingInput } from './RatingInput'
import { errText, useToast } from './ui'

export function MovieCard({ movie, children }: { movie: Movie; children?: React.ReactNode }) {
  const { rate, clear } = useRating()
  const toast = useToast()
  const pending = rate.isPending ? rate.variables?.rating : undefined
  // Optimistic: show the rating just clicked at once; it snaps back to the server value on error.
  const value = pending ?? movie.my_rating
  return (
    <article className="flex h-full flex-col justify-between p-4">
      <div>
        <p className="micro flex justify-between opacity-70">
          <span>Film</span>
          <span className="num">ID {String(movie.id).padStart(4, '0')}</span>
        </p>
        <Link to={`/movies/${movie.id}`} className="display mt-2 block text-[1.05rem] leading-[1.02] tracking-[-0.02em] hover:text-alert">
          {movie.title}
        </Link>
        <p className="micro mt-2">{movie.genres.join(' / ') || 'Unclassified'}</p>
        {movie.avg_rating_train != null && (
          <p className="micro num mt-1 opacity-70">
            Avg {movie.avg_rating_train.toFixed(2)} · {movie.n_ratings_train} ratings
          </p>
        )}
        {children}
      </div>
      <div className="mt-4">
        <RatingInput
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
