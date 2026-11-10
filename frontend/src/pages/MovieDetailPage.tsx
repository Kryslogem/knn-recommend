import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { get } from '../api/client'
import { useRating } from '../api/hooks'
import type { Movie, Prediction } from '../api/types'
import { ExplainDrawer } from '../components/ExplainDrawer'
import { RatingInput } from '../components/RatingInput'
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
    <div className="space-y-6">
      <Link to="/movies" className="micro underline hover:text-alert">
        &lt;&lt;&lt; Back to catalog
      </Link>
      <div className="border-b-4 border-ink pb-4">
        <p className="micro num">Film / ID {String(m.id).padStart(4, '0')}</p>
        <h1 className="display mt-2 text-[clamp(2rem,6vw,4.5rem)]">{m.title}</h1>
        <p className="micro mt-3">
          {m.genres.join(' / ')} {m.release_date && `· Released ${m.release_date}`}
        </p>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Community data">
          {m.avg_rating_train != null ? (
            <p>
              Average rating <b className="display num text-3xl">{m.avg_rating_train.toFixed(2)}</b> from {m.n_ratings_train} ratings (MovieLens training data).
            </p>
          ) : (
            <p>This film is not in the model's training data.</p>
          )}
          <div className="mt-5">
            <p className="micro mb-2">Your rating</p>
            <RatingInput
              value={value}
              disabled={rate.isPending || clear.isPending}
              onChange={(rating) => rate.mutate({ movieId: id, rating }, { onError: (e) => toast('err', errText(e)) })}
              onClear={() => clear.mutate(id, { onError: (e) => toast('err', errText(e)) })}
            />
          </div>
        </Card>

        <Card title="Predicted rating for you">
          {pred.isLoading && <Skeleton className="h-16" />}
          {pred.error && <ErrorState error={pred.error} retry={() => pred.refetch()} />}
          {pred.data && !item && <p>{pred.data.message ?? 'No prediction is available for this film.'}</p>}
          {item && (
            <div className="flex flex-wrap items-center gap-4">
              <span className="display num text-6xl">{item.predicted_rating.toFixed(2)}</span>
              <div className="space-y-2">
                <SourceBadge source={item.source} />
                <div>
                  <Button variant="ghost" onClick={() => setOpen(true)}>
                    Why? &gt;&gt;&gt;
                  </Button>
                </div>
              </div>
              {pred.data!.profile_size === 0 && <p className="micro w-full">Rate a few films to get a personalized prediction.</p>}
            </div>
          )}
          <p className="micro mt-4 opacity-70">A predicted rating is not the probability that you will like the film.</p>
        </Card>
      </div>
      {open && item && <ExplainDrawer item={item} onClose={() => setOpen(false)} />}
    </div>
  )
}
