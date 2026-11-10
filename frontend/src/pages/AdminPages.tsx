import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { get, qs, send } from '../api/client'
import type { AdminMovie, AdminStatus, AdminUser, Page, Recommendations, Role } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { PageTitle } from '../components/Layout'
import { Button, Card, EmptyState, ErrorState, Pagination, SkeletonGrid, SourceBadge, Spinner, Stat, errText, useDebounce, useToast } from '../components/ui'

const pct = (x: number | null) => (x == null ? '-' : `${(x * 100).toFixed(1)}%`)
const ms = (x: number | null) => (x == null ? '-' : `${x} ms`)

function MovieLensDemo() {
  const [id, setId] = useState('')
  const [target, setTarget] = useState<number | null>(null)
  const idNum = Number(id)
  const valid = Number.isInteger(idNum) && idNum >= 1 && idNum <= 943
  const q = useQuery({
    queryKey: ['admin-ml', target],
    queryFn: () => get<Recommendations>(`/admin/recommendations/movielens/${target}?n=10`),
    enabled: target !== null,
  })
  return (
    <Card title="Recommendations for a MovieLens profile (demo)">
      <form
        className="flex flex-wrap items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          if (valid) setTarget(idNum)
        }}
      >
        <input className="field !w-36" placeholder="ID 1-943" aria-label="MovieLens user ID" inputMode="numeric" value={id} onChange={(e) => setId(e.target.value.replace(/\D/g, ''))} />
        <Button type="submit" disabled={!valid}>
          Show &gt;&gt;&gt;
        </Button>
        {id && !valid && <span className="font-bold text-alert">/// ID must be between 1 and 943</span>}
      </form>
      {q.isLoading && <Spinner />}
      {q.error && <ErrorState error={q.error} />}
      {q.data && (
        <>
          <p className="micro mt-4">
            Profile #{q.data.ml_user_id} has {q.data.profile_size} films in the training split. That profile itself is excluded from its own neighbours.
          </p>
          <ol className="ruled mt-2">
            {q.data.items.map((it, i) => (
              <li key={it.movie.id} className="flex items-center gap-3 px-3 py-2">
                <span className="num w-6 opacity-50">{String(i + 1).padStart(2, '0')}</span>
                <span className="flex-1">{it.movie.title}</span>
                <b className="num">{it.predicted_rating.toFixed(2)}</b>
                <SourceBadge source={it.source} />
              </li>
            ))}
          </ol>
        </>
      )}
    </Card>
  )
}

export function AdminOverview() {
  const q = useQuery({ queryKey: ['admin-status'], queryFn: () => get<AdminStatus>('/admin/status'), refetchInterval: 10000 })
  if (q.isLoading) return <Spinner />
  if (q.error) return <ErrorState error={q.error} retry={() => q.refetch()} />
  const s = q.data!
  return (
    <div className="space-y-8">
      <PageTitle title="System overview" subtitle="Refreshes automatically every 10 seconds." />
      <div className="ruled grid-cols-2 lg:grid-cols-4">
        <Stat label="Accounts" value={s.users.app} hint={`+ ${s.users.movielens} MovieLens profiles`} />
        <Stat label="Films" value={s.movies.total} hint={`${s.movies.hidden} hidden`} />
        <Stat label="Web ratings" value={s.ratings.app} hint={`${s.ratings.movielens.toLocaleString('en-US')} MovieLens (train)`} />
        <Stat label="Training" value={s.training_running ? 'Running' : 'Idle'} />
      </div>
      <Card title="Model in service">
        {s.model.loaded ? (
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <dt className="micro opacity-70">Version</dt>
              <dd className="break-all font-bold">{s.model.version}</dd>
            </div>
            <div>
              <dt className="micro opacity-70">Loaded at (UTC)</dt>
              <dd className="num font-bold">{s.model.loaded_at?.replace('T', ' ').slice(0, 19)}</dd>
            </div>
            <div>
              <dt className="micro opacity-70">Minimum ratings per film</dt>
              <dd className="num font-bold">{s.model.min_item_ratings}</dd>
            </div>
          </dl>
        ) : (
          <p className="font-bold text-alert">/// No model is active. A data scientist needs to train and activate a version.</p>
        )}
      </Card>
      <Card title="Recommendation performance (last 500 computed requests)">
        <div className="ruled grid-cols-2 lg:grid-cols-4">
          <Stat label="Requests" value={s.recommendations.requests} hint="cache hits not counted" />
          <Stat label="Latency p50" value={ms(s.recommendations.p50_ms)} />
          <Stat label="Latency p95" value={ms(s.recommendations.p95_ms)} hint="target: under 2000 ms" />
          <Stat label="Fallback rate" value={pct(s.recommendations.fallback_rate)} hint="items not based on KNN" />
        </div>
      </Card>
      <MovieLensDemo />
    </div>
  )
}

const ROLES: { v: Role; l: string }[] = [
  { v: 'user', l: 'User' },
  { v: 'data_scientist', l: 'Data scientist' },
  { v: 'admin', l: 'Admin' },
]

export function AdminUsers() {
  const { user: me } = useAuth()
  const qc = useQueryClient()
  const toast = useToast()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const dq = useDebounce(search.trim())
  const q = useQuery({
    queryKey: ['admin-users', dq, page],
    queryFn: () => get<Page<AdminUser>>(`/admin/users${qs({ q: dq, page, page_size: 20 })}`),
    placeholderData: keepPreviousData,
  })
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { role?: Role; is_active?: boolean } }) => send('PATCH', `/admin/users/${id}`, body),
    onSuccess: () => {
      toast('ok', 'Account updated')
      qc.invalidateQueries({ queryKey: ['admin-users'] })
    },
    onError: (e) => toast('err', errText(e)),
  })
  return (
    <div>
      <PageTitle title="Accounts" subtitle="Change a role or lock/unlock an account. You cannot modify your own account." />
      <input
        className="field mb-6 !w-72"
        placeholder="Search username…"
        aria-label="Search username"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value)
          setPage(1)
        }}
      />
      {q.isLoading && <Spinner />}
      {q.error && <ErrorState error={q.error} retry={() => q.refetch()} />}
      {q.data && q.data.items.length === 0 && <EmptyState title="No matching accounts" />}
      {q.data && q.data.items.length > 0 && (
        <>
          <div className="panel overflow-x-auto p-2">
            <table className="table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {q.data.items.map((u) => {
                  const self = u.id === me?.id
                  return (
                    <tr key={u.id}>
                      <td className="font-bold">
                        {u.username} {self && <span className="tag ml-1">you</span>}
                      </td>
                      <td>
                        <select className="field !w-auto !py-1" aria-label={`Role of ${u.username}`} disabled={self || patch.isPending} value={u.role} onChange={(e) => patch.mutate({ id: u.id, body: { role: e.target.value as Role } })}>
                          {ROLES.map((r) => (
                            <option key={r.v} value={r.v}>
                              {r.l}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <Button variant={u.is_active ? 'ghost' : 'primary'} className="btn-sm" disabled={self || patch.isPending} onClick={() => patch.mutate({ id: u.id, body: { is_active: !u.is_active } })}>
                          {u.is_active ? 'Lock' : 'Unlock'}
                        </Button>{' '}
                        <span className={`micro ${u.is_active ? '' : 'font-bold text-alert'}`}>{u.is_active ? 'Active' : 'Locked'}</span>
                      </td>
                      <td className="micro num">{u.created_at.slice(0, 10)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <Pagination page={q.data.page} pageSize={q.data.page_size} total={q.data.total} onChange={setPage} />
        </>
      )}
    </div>
  )
}

export function AdminMovies() {
  const qc = useQueryClient()
  const toast = useToast()
  const [search, setSearch] = useState('')
  const [hidden, setHidden] = useState('')
  const [page, setPage] = useState(1)
  const dq = useDebounce(search.trim())
  const q = useQuery({
    queryKey: ['admin-movies', dq, hidden, page],
    queryFn: () => get<Page<AdminMovie>>(`/admin/movies${qs({ q: dq, hidden: hidden || undefined, page, page_size: 20 })}`),
    placeholderData: keepPreviousData,
  })
  const patch = useMutation({
    mutationFn: ({ id, is_hidden }: { id: number; is_hidden: boolean }) => send('PATCH', `/admin/movies/${id}`, { is_hidden }),
    onSuccess: (_, v) => {
      toast('ok', v.is_hidden ? 'Film hidden from the catalog and recommendations' : 'Film is visible again')
      qc.invalidateQueries({ queryKey: ['admin-movies'] })
      for (const k of ['movies', 'recs', 'popular']) qc.invalidateQueries({ queryKey: [k] })
    },
    onError: (e) => toast('err', errText(e)),
  })
  return (
    <div>
      <PageTitle title="Catalog admin" subtitle="Hide a film from the catalog and from every user's recommendations." />
      <div className="mb-6 flex flex-wrap gap-3">
        <input
          className="field !w-72"
          placeholder="Search title…"
          aria-label="Search by title"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
        />
        <select
          className="field !w-auto"
          aria-label="Filter by status"
          value={hidden}
          onChange={(e) => {
            setHidden(e.target.value)
            setPage(1)
          }}
        >
          <option value="">All</option>
          <option value="false">Visible</option>
          <option value="true">Hidden</option>
        </select>
      </div>
      {q.isLoading && <SkeletonGrid n={4} />}
      {q.error && <ErrorState error={q.error} retry={() => q.refetch()} />}
      {q.data && q.data.items.length === 0 && <EmptyState title="No matching films" />}
      {q.data && q.data.items.length > 0 && (
        <>
          <div className="panel overflow-x-auto p-2">
            <table className="table">
              <thead>
                <tr>
                  <th>Film</th>
                  <th>Genres</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {q.data.items.map((m) => (
                  <tr key={m.id}>
                    <td className="font-bold">{m.title}</td>
                    <td className="micro">{m.genres.join(' / ')}</td>
                    <td>
                      <Button variant={m.is_hidden ? 'primary' : 'ghost'} className="btn-sm" disabled={patch.isPending} onClick={() => patch.mutate({ id: m.id, is_hidden: !m.is_hidden })}>
                        {m.is_hidden ? 'Unhide' : 'Hide'}
                      </Button>{' '}
                      {m.is_hidden && <span className="tag tag-alert">Hidden</span>}
                    </td>
                  </tr>
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
