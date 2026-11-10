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
      <PageTitle title="Tell us your taste" subtitle={`Rate at least ${GOAL} films you have seen to unlock personalized recommendations. Skip anything you have not watched.`} />
      <div className="sticky top-0 z-10 border-2 border-ink bg-paper p-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="micro num">
            Rated <b className="text-base">{n}</b> / {GOAL}
          </span>
          <Link to="/recommendations">
            <Button disabled={!done}>{done ? 'See my recommendations >>>' : `${GOAL - n} more to go`}</Button>
          </Link>
        </div>
        <div className="mt-2 h-3 border-2 border-ink" role="progressbar" aria-valuenow={Math.min(n, GOAL)} aria-valuemin={0} aria-valuemax={GOAL}>
          <div className="h-full bg-alert" style={{ width: `${Math.min(100, (n / GOAL) * 100)}%` }} />
        </div>
      </div>
      <PopularGrid n={16} />
      <p className="micro">
        Cannot find a film you know? Search the <Link to="/movies" className="underline hover:text-alert">catalog</Link> by title.
      </p>
    </div>
  )
}
