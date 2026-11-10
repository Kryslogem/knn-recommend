import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../api/client'
import type { ModelVersion } from '../api/types'
import { PageTitle } from '../components/Layout'
import { Button, ErrorState, Spinner, errText, useToast } from '../components/ui'

const f4 = (x: number | undefined) => (x === undefined ? '—' : x.toFixed(4))

export function DsModels() {
  const qc = useQueryClient()
  const toast = useToast()
  const q = useQuery({ queryKey: ['ds-models'], queryFn: () => get<{ items: ModelVersion[] }>('/ds/models') })
  const activate = useMutation({
    mutationFn: (id: number) => send('POST', `/ds/models/${id}/activate`),
    onSuccess: () => {
      toast('ok', 'Đã kích hoạt — mô hình mới phục vụ ngay, không cần khởi động lại')
      qc.invalidateQueries({ queryKey: ['ds-models'] })
      qc.invalidateQueries({ queryKey: ['recs'] })
      qc.invalidateQueries({ queryKey: ['admin-status'] })
    },
    onError: (e) => toast('err', errText(e)),
  })
  if (q.isLoading) return <Spinner />
  if (q.error) return <ErrorState error={q.error} retry={() => q.refetch()} />
  const items = q.data!.items
  return (
    <div>
      <PageTitle title="Phiên bản mô hình" subtitle="Mỗi phiên bản là bất biến (artifact + cấu hình + hash dữ liệu). Chỉ một phiên bản được phục vụ tại một thời điểm." />
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white p-4">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase text-slate-500">
            <tr><th className="pb-2">Phiên bản</th><th>Cấu hình</th><th>RMSE val</th><th>NDCG@10 val (lọc)</th><th>Metrics test</th><th>Tạo lúc</th><th /></tr>
          </thead>
          <tbody>
            {items.map((m) => {
              const thr = m.config.serving.min_item_ratings
              const p = m.config.params
              return (
                <tr key={m.id} className="border-t border-slate-100 align-top">
                  <td className="py-2 pr-2"><div className="font-mono text-xs">{m.version}</div>{m.is_active && <span className="mt-1 inline-block rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800">Đang phục vụ</span>}</td>
                  <td className="pr-2 text-xs text-slate-600">K={p.k}, min_k={p.min_k}, shr={p.shrinkage}, reg={p.reg_u}/{p.reg_i}, thr={thr}</td>
                  <td>{f4(m.metrics_val?.rmse)}</td>
                  <td>{f4(m.metrics_val?.[`ndcg@10_min${thr}`])}</td>
                  <td className="text-xs">{m.has_test_metrics ? 'có (đánh giá chính thức)' : '—'}</td>
                  <td className="text-xs text-slate-500">{m.created_at.replace('T', ' ').slice(0, 19)}</td>
                  <td>
                    <Button
                      variant={m.is_active ? 'ghost' : 'primary'}
                      disabled={m.is_active || activate.isPending}
                      onClick={() => window.confirm(`Kích hoạt phiên bản ${m.version}? Đề xuất của mọi người dùng sẽ dùng mô hình này.`) && activate.mutate(m.id)}
                    >
                      {m.is_active ? 'Đang dùng' : 'Kích hoạt'}
                    </Button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {items.length === 0 && <p className="text-sm text-slate-500">Chưa có phiên bản nào. Chạy <code>scripts/train.py</code> hoặc tạo job ở trang Huấn luyện.</p>}
      </div>
    </div>
  )
}
