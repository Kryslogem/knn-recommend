import { useMutation, useQueryClient } from '@tanstack/react-query'
import { send } from './client'

/** Rate / clear a rating. Afterwards refresh recommendations, history and catalog (NFR03).
 *  Deliberately does NOT refresh the "popular" list so cards do not vanish under the cursor while rating. */
export function useRating() {
  const qc = useQueryClient()
  const invalidate = () => {
    for (const key of ['recs', 'history', 'movies', 'movie', 'prediction', 'me']) qc.invalidateQueries({ queryKey: [key] })
  }
  const rate = useMutation({
    mutationFn: ({ movieId, rating }: { movieId: number; rating: number }) => send('PUT', `/ratings/${movieId}`, { rating }),
    onSuccess: invalidate,
  })
  const clear = useMutation({
    mutationFn: (movieId: number) => send('DELETE', `/ratings/${movieId}`),
    onSuccess: invalidate,
  })
  return { rate, clear }
}
