import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { get, qs, send } from '../api/client'
import type { AdminMovie, AdminStatus, AdminUser, Page, Recommendations, Role } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { PageTitle } from '../components/Layout'
import { Button, Card, EmptyState, ErrorState, Pagination, SkeletonGrid, SourceBadge, Spinner, Stat, errText, useDebounce, useToast } from '../components/ui'

const pct = (x: number | null) => (x == null ? '—' : `${(x * 100).toFixed(1)}%`)
const ms = (x: number | null) => (x == null ? '—' : `${x} ms`)

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
    <Card title="Đề xuất cho một hồ sơ MovieLens (minh họa)">
      <form
        className="flex flex-wrap items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          if (valid) setTarget(idNum)
        }}
      >
        <input className="w-32 rounded-md border border-slate-300 px-3 py-1.5 text-sm" placeholder="ID 1–943" aria-label="ID người dùng MovieLens" inputMode="numeric" value={id} onChange={(e) => setId(e.target.value.replace(/\D/g, ''))} />
        <Button type="submit" disabled={!valid}>
          Xem đề xuất
        </Button>
        {id && !valid && <span className="text-sm text-red-600">ID phải từ 1 đến 943</span>}
      </form>
      {q.isLoading && <Spinner />}
      {q.error && <ErrorState error={q.error} />}
      {q.data && (
        <>
          <p className="mt-3 text-xs text-slate-500">
            Hồ sơ #{q.data.ml_user_id} có {q.data.profile_size} phim trong tập train; chính hồ sơ này bị loại khỏi láng giềng.
          </p>
          <ol className="mt-2 space-y-1 text-sm">
            {q.data.items.map((it, i) => (
              <li key={it.movie.id} className="flex items-center gap-2">
                <span className="w-5 text-slate-400">{i + 1}.</span>
                <span className="flex-1">{it.movie.title}</span>
                <b>{it.predicted_rating.toFixed(2)}</b>
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
    <div className="space-y-6">
      <PageTitle title="Tổng quan hệ thống" subtitle="Tự làm mới mỗi 10 giây." />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Tài khoản" value={s.users.app} hint={`+ ${s.users.movielens} hồ sơ MovieLens`} />
        <Stat label="Phim" value={s.movies.total} hint={`${s.movies.hidden} đang bị ẩn`} />
        <Stat label="Đánh giá từ web" value={s.ratings.app} hint={`${s.ratings.movielens.toLocaleString('vi-VN')} từ MovieLens (train)`} />
        <Stat label="Huấn luyện" value={s.training_running ? 'Đang chạy' : 'Rảnh'} />
      </div>
      <Card title="Mô hình đang phục vụ">
        {s.model.loaded ? (
          <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Phiên bản</dt>
              <dd className="font-mono">{s.model.version}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Nạp lúc (UTC)</dt>
              <dd>{s.model.loaded_at?.replace('T', ' ').slice(0, 19)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Ngưỡng tối thiểu số rating của phim</dt>
              <dd>{s.model.min_item_ratings}</dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-amber-700">Chưa có mô hình nào được kích hoạt. Data Scientist cần huấn luyện và kích hoạt một phiên bản.</p>
        )}
      </Card>
      <Card title="Hiệu năng đề xuất (tối đa 500 lượt gần nhất)">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Stat label="Số lượt tính" value={s.recommendations.requests} hint="không tính lượt lấy từ bộ nhớ đệm" />
          <Stat label="Độ trễ p50" value={ms(s.recommendations.p50_ms)} />
          <Stat label="Độ trễ p95" value={ms(s.recommendations.p95_ms)} hint="mục tiêu < 2000 ms" />
          <Stat label="Tỉ lệ fallback" value={pct(s.recommendations.fallback_rate)} hint="đề xuất không dựa trên KNN" />
        </div>
      </Card>
      <MovieLensDemo />
    </div>
  )
}

const ROLES: { v: Role; l: string }[] = [
  { v: 'user', l: 'Người dùng' },
  { v: 'data_scientist', l: 'Data Scientist' },
  { v: 'admin', l: 'Quản trị viên' },
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
      toast('ok', 'Đã cập nhật')
      qc.invalidateQueries({ queryKey: ['admin-users'] })
    },
    onError: (e) => toast('err', errText(e)),
  })
  return (
    <div>
      <PageTitle title="Quản lý tài khoản" subtitle="Đổi vai trò hoặc khóa/mở tài khoản. Không thể tự sửa chính mình." />
      <input className="mb-4 w-64 rounded-md border border-slate-300 px-3 py-1.5 text-sm" placeholder="Tìm tên đăng nhập…" aria-label="Tìm tên đăng nhập" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
      {q.isLoading && <Spinner />}
      {q.error && <ErrorState error={q.error} retry={() => q.refetch()} />}
      {q.data && q.data.items.length === 0 && <EmptyState title="Không có tài khoản phù hợp" />}
      {q.data && q.data.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white p-4">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
                <tr><th className="pb-2">Tên đăng nhập</th><th className="pb-2">Vai trò</th><th className="pb-2">Trạng thái</th><th className="pb-2">Tạo lúc</th></tr>
              </thead>
              <tbody>
                {q.data.items.map((u) => {
                  const self = u.id === me?.id
                  return (
                    <tr key={u.id} className="border-t border-slate-100">
                      <td className="py-2">{u.username} {self && <span className="text-xs text-slate-400">(bạn)</span>}</td>
                      <td className="py-2">
                        <select className="rounded border border-slate-300 px-2 py-1" aria-label={`Vai trò của ${u.username}`} disabled={self || patch.isPending} value={u.role} onChange={(e) => patch.mutate({ id: u.id, body: { role: e.target.value as Role } })}>
                          {ROLES.map((r) => <option key={r.v} value={r.v}>{r.l}</option>)}
                        </select>
                      </td>
                      <td className="py-2">
                        <Button variant={u.is_active ? 'ghost' : 'primary'} disabled={self || patch.isPending} onClick={() => patch.mutate({ id: u.id, body: { is_active: !u.is_active } })}>
                          {u.is_active ? 'Khóa' : 'Mở khóa'}
                        </Button>{' '}
                        <span className={`text-xs ${u.is_active ? 'text-emerald-700' : 'text-red-600'}`}>{u.is_active ? 'Hoạt động' : 'Đã khóa'}</span>
                      </td>
                      <td className="py-2 text-xs text-slate-500">{u.created_at.slice(0, 10)}</td>
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
      toast('ok', v.is_hidden ? 'Đã ẩn phim khỏi danh mục và đề xuất' : 'Đã hiện lại phim')
      qc.invalidateQueries({ queryKey: ['admin-movies'] })
      for (const k of ['movies', 'recs', 'popular']) qc.invalidateQueries({ queryKey: [k] })
    },
    onError: (e) => toast('err', errText(e)),
  })
  return (
    <div>
      <PageTitle title="Quản lý danh mục phim" subtitle="Ẩn phim khỏi danh mục và danh sách đề xuất của mọi người dùng." />
      <div className="mb-4 flex flex-wrap gap-3">
        <input className="w-64 rounded-md border border-slate-300 px-3 py-1.5 text-sm" placeholder="Tìm theo tên phim…" aria-label="Tìm theo tên phim" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
        <select className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm" aria-label="Lọc trạng thái" value={hidden} onChange={(e) => { setHidden(e.target.value); setPage(1) }}>
          <option value="">Tất cả</option><option value="false">Đang hiện</option><option value="true">Đang ẩn</option>
        </select>
      </div>
      {q.isLoading && <SkeletonGrid n={4} />}
      {q.error && <ErrorState error={q.error} retry={() => q.refetch()} />}
      {q.data && q.data.items.length === 0 && <EmptyState title="Không có phim phù hợp" />}
      {q.data && q.data.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white p-4">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500"><tr><th className="pb-2">Phim</th><th className="pb-2">Thể loại</th><th className="pb-2">Trạng thái</th></tr></thead>
              <tbody>
                {q.data.items.map((m) => (
                  <tr key={m.id} className="border-t border-slate-100">
                    <td className="py-2">{m.title}</td>
                    <td className="py-2 text-xs text-slate-500">{m.genres.join(' · ')}</td>
                    <td className="py-2">
                      <Button variant={m.is_hidden ? 'primary' : 'ghost'} disabled={patch.isPending} onClick={() => patch.mutate({ id: m.id, is_hidden: !m.is_hidden })}>
                        {m.is_hidden ? 'Hiện lại' : 'Ẩn'}
                      </Button>{' '}
                      {m.is_hidden && <span className="text-xs text-red-600">Đang ẩn</span>}
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
