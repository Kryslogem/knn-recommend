import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { get, send } from '../api/client'
import type { ModelVersion } from '../api/types'
import { PageTitle } from '../components/Layout'
import { Button, ErrorState, Spinner, errText, useToast } from '../components/ui'

const f4 = (x: number | undefined) => (x === undefined ? '-' : x.toFixed(4))

export function DsModels() {
  const qc = useQueryClient()
  const toast = useToast()
  const q = useQuery({ queryKey: ['ds-models'], queryFn: () => get<{ items: ModelVersion[] }>('/ds/models') })
  const activate = useMutation({
    mutationFn: (id: number) => send('POST', `/ds/models/${id}/activate`),
    onSuccess: () => {
      toast('ok', 'Activated. The new model serves requests immediately, no restart needed.')
      qc.invalidateQueries({ queryKey: ['ds-models'] })
      qc.invalidateQueries({ queryKey: ['recs'] })
      qc.invalidateQueries({ queryKey: ['admin-status'] })
      qc.invalidateQueries({ queryKey: ['health'] })
    },
    onError: (e) => toast('err', errText(e)),
  })
  if (q.isLoading) return <Spinner />
  if (q.error) return <ErrorState error={q.error} retry={() => q.refetch()} />
  const items = q.data!.items
  return (
    <div>
      <PageTitle title="Model versions" subtitle="Each version is immutable: artifact, configuration and data hashes. Exactly one version serves requests at a time." />
      <div className="panel overflow-x-auto p-2">
        <table className="table">
          <thead>
            <tr>
              <th>Version</th>
              <th>Configuration</th>
              <th>RMSE val</th>
              <th>NDCG@10 val</th>
              <th>Test metrics</th>
              <th>Created (UTC)</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((m) => {
              const thr = m.config.serving.min_item_ratings
              const p = m.config.params
              return (
                <tr key={m.id}>
                  <td>
                    <div className="break-all font-bold">{m.version}</div>
                    {m.is_active && <span className="tag tag-solid mt-1">In service</span>}
                  </td>
                  <td className="micro num">
                    K={p.k} min_k={p.min_k} shr={p.shrinkage} reg={p.reg_u}/{p.reg_i} thr={thr}
                  </td>
                  <td className="num">{f4(m.metrics_val?.rmse)}</td>
                  <td className="num">{f4(m.metrics_val?.[`ndcg@10_min${thr}`])}</td>
                  <td className="micro">{m.has_test_metrics ? 'Official evaluation' : '-'}</td>
                  <td className="micro num">{m.created_at.replace('T', ' ').slice(0, 19)}</td>
                  <td>
                    <Button
                      variant={m.is_active ? 'ghost' : 'primary'}
                      className="btn-sm"
                      disabled={m.is_active || activate.isPending}
                      onClick={() => window.confirm(`Activate ${m.version}? Every user's recommendations will use this model.`) && activate.mutate(m.id)}
                    >
                      {m.is_active ? 'Active' : 'Activate'}
                    </Button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {items.length === 0 && <p className="p-3">No versions yet. Run <code>scripts/train.py</code> or start a job on the Training page.</p>}
      </div>
    </div>
  )
}
