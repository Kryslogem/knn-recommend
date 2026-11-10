import { useMutation, useQueryClient } from '@tanstack/react-query'
import { send } from './client'

/** Chấm / xóa điểm. Sau khi đổi, làm mới đề xuất, lịch sử và danh mục (NFR03).
 *  Cố ý KHÔNG làm mới danh sách "phổ biến" để thẻ không biến mất ngay dưới con trỏ khi đang chấm. */
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
