import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { get } from '../api/client'
import type { User } from '../api/types'
import { PageTitle } from '../components/Layout'
import { Button } from '../components/ui'
import { PopularGrid } from './HomePage'

const GOAL = 5

export function OnboardingPage() {
  const me = useQuery({ queryKey: ['me'], queryFn: () => get<User>('/auth/me') })
  const n = me.data?.n_ratings ?? 0
  const done = n >= GOAL
  return (
    <div className="space-y-6">
      <PageTitle title="Hãy cho chúng tôi biết gu của bạn" subtitle={`Chấm điểm ít nhất ${GOAL} phim bạn đã xem để bắt đầu nhận đề xuất cá nhân hóa. Phim chưa xem cứ bỏ qua.`} />
      <div className="sticky top-0 z-10 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
        <div className="flex items-center justify-between text-sm">
          <span>
            Đã chấm <b>{n}</b>/{GOAL} phim
          </span>
          <Link to="/recommendations">
            <Button disabled={!done}>{done ? 'Xem đề xuất của tôi →' : `Cần thêm ${GOAL - n} phim`}</Button>
          </Link>
        </div>
        <div className="mt-2 h-2 rounded bg-slate-100" role="progressbar" aria-valuenow={Math.min(n, GOAL)} aria-valuemin={0} aria-valuemax={GOAL}>
          <div className="h-2 rounded bg-indigo-600 transition-all" style={{ width: `${Math.min(100, (n / GOAL) * 100)}%` }} />
        </div>
      </div>
      <PopularGrid n={16} />
      <p className="text-sm text-slate-500">
        Không thấy phim bạn biết? Dùng <Link to="/movies" className="text-indigo-700 underline">Danh mục phim</Link> để tìm theo tên.
      </p>
    </div>
  )
}
