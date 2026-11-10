import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { get } from '../api/client'
import type { CompareRow, Comparison, ErrorAnalysis, GroupRow, TuningRow } from '../api/types'
import { PageTitle } from '../components/Layout'
import { Card, ErrorState, Spinner } from '../components/ui'

const COLORS = ['#4f46e5', '#0891b2', '#dc2626', '#d97706', '#059669', '#7c3aed']
const f4 = (x: unknown) => (typeof x === 'number' ? x.toFixed(4) : '—')

function CompareTable({ rows, thr }: { rows: CompareRow[]; thr: number }) {
  const cols: { key: string; label: string; best: 'min' | 'max' }[] = [
    { key: 'rmse', label: 'RMSE', best: 'min' },
    { key: 'mae', label: 'MAE', best: 'min' },
    { key: `precision@10_min${thr}`, label: `P@10 (≥${thr})`, best: 'max' },
    { key: `recall@10_min${thr}`, label: `R@10 (≥${thr})`, best: 'max' },
    { key: `ndcg@10_min${thr}`, label: `NDCG@10 (≥${thr})`, best: 'max' },
    { key: 'ndcg@10', label: 'NDCG@10 (không lọc)', best: 'max' },
    { key: `catalog_coverage_min${thr}`, label: 'Độ phủ danh mục', best: 'max' },
    { key: 'prediction_coverage_knn', label: 'Dự đoán bằng KNN', best: 'max' },
  ]
  const best = (key: string, mode: 'min' | 'max') => {
    const v = rows.map((r) => r[key] as number)
    return mode === 'min' ? Math.min(...v) : Math.max(...v)
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs uppercase text-slate-500">
          <tr><th className="pb-2">Mô hình</th>{cols.map((c) => <th key={c.key} className="pb-2 pr-2">{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.model} className="border-t border-slate-100">
              <td className="py-2 pr-3 font-medium">{r.label}</td>
              {cols.map((c) => {
                const v = r[c.key] as number
                const isBest = v === best(c.key, c.best)
                return <td key={c.key} className={`pr-2 font-mono ${isBest ? 'font-bold text-emerald-700' : ''}`}>{f4(v)}</td>
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-slate-500">In đậm xanh = tốt nhất mỗi cột. MAE/RMSE tính trên mọi cặp giữ lại, kể cả cặp phải fallback. Xếp hạng tính trên người có ≥ 1 phim liên quan (rating ≥ 4).</p>
    </div>
  )
}

function GroupChart({ title, rows }: { title: string; rows: GroupRow[] }) {
  return (
    <Card title={title}>
      <div className="h-56">
        <ResponsiveContainer>
          <BarChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="group" tick={{ fontSize: 11 }} />
            <YAxis domain={[0.6, 'auto']} />
            <Tooltip formatter={(v) => (typeof v === 'number' ? v.toFixed(3) : v)} />
            <Legend />
            <Bar dataKey="rmse_knn_baseline" name="KNNBaseline" fill="#4f46e5" />
            <Bar dataKey="rmse_bias_only" name="Bias-only" fill="#94a3b8" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

export function DsEvaluation() {
  const [split, setSplit] = useState<'test' | 'validation'>('test')
  const cmp = useQuery({ queryKey: ['ds-cmp'], queryFn: () => get<Comparison>('/ds/evaluation/comparison') })
  const tune = useQuery({ queryKey: ['ds-tune'], queryFn: () => get<{ items: TuningRow[] }>('/ds/evaluation/tuning') })
  const err = useQuery({ queryKey: ['ds-err'], queryFn: () => get<ErrorAnalysis>('/ds/evaluation/errors') })

  const thr = cmp.data?.config.serving.min_item_ratings ?? 0
  const rows = cmp.data?.rows.filter((r) => r.split === split) ?? []

  // Đường cong tuning: giữ các siêu tham số khác ở giá trị của cấu hình tốt nhất, thay đổi K và shrinkage.
  let curves: Record<string, number | string>[] = []
  let shrinks: number[] = []
  if (tune.data) {
    const t = tune.data.items
    const best = [...t].sort((a, b) => (a.val_rmse ?? 9) - (b.val_rmse ?? 9))[0]
    if (best) {
      const sub = t.filter((r) => r.reg_u === best.reg_u && r.reg_i === best.reg_i && r.min_support === best.min_support && r.min_k === best.min_k)
      shrinks = [...new Set(sub.map((r) => r.shrinkage as number))].sort((a, b) => a - b)
      curves = [...new Set(sub.map((r) => r.k as number))].sort((a, b) => a - b).map((k) => {
        const o: Record<string, number | string> = { k }
        for (const s of shrinks) o[`s${s}`] = sub.find((r) => r.k === k && r.shrinkage === s)?.val_rmse ?? NaN
        return o
      })
    }
  }

  return (
    <div className="space-y-6">
      <PageTitle title="Đánh giá mô hình" subtitle="So sánh 5 mô hình trên cùng split, cùng tập ứng viên và cùng quy tắc fallback." />

      <Card title="Bảng so sánh">
        <div className="mb-3 flex gap-2" role="tablist">
          {(['test', 'validation'] as const).map((s) => (
            <button key={s} role="tab" aria-selected={split === s} onClick={() => setSplit(s)} className={`rounded-md px-3 py-1 text-sm ${split === s ? 'bg-indigo-600 text-white' : 'border border-slate-300 bg-white text-slate-700'}`}>
              {s === 'test' ? 'Test (đánh giá cuối)' : 'Validation (dùng để chọn tham số)'}
            </button>
          ))}
        </div>
        {cmp.isLoading && <Spinner />}
        {cmp.error && <ErrorState error={cmp.error} retry={() => cmp.refetch()} />}
        {cmp.data && <CompareTable rows={rows} thr={thr} />}
      </Card>

      {cmp.data && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card title={`RMSE (${split})`}>
            <div className="h-56"><ResponsiveContainer><BarChart data={rows} layout="vertical" margin={{ left: 90 }}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" domain={[0.8, 'auto']} /><YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={170} /><Tooltip formatter={(v) => (typeof v === 'number' ? v.toFixed(4) : v)} /><Bar dataKey="rmse" fill="#4f46e5" /></BarChart></ResponsiveContainer></div>
          </Card>
          <Card title={`NDCG@10 với ngưỡng ≥ ${thr} rating (${split})`}>
            <div className="h-56"><ResponsiveContainer><BarChart data={rows} layout="vertical" margin={{ left: 90 }}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" /><YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={170} /><Tooltip formatter={(v) => (typeof v === 'number' ? v.toFixed(4) : v)} /><Bar dataKey={`ndcg@10_min${thr}`} fill="#0891b2" /></BarChart></ResponsiveContainer></div>
          </Card>
        </div>
      )}

      <Card title="Tuning trên validation: RMSE theo K và shrinkage">
        {tune.isLoading && <Spinner />}
        {tune.error && <ErrorState error={tune.error} retry={() => tune.refetch()} />}
        {curves.length > 0 && (
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={curves}>
                <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="k" label={{ value: 'K', position: 'insideBottom', offset: -2 }} /><YAxis domain={['auto', 'auto']} /><Tooltip formatter={(v) => (typeof v === 'number' ? v.toFixed(4) : v)} /><Legend />
                {shrinks.map((s, i) => <Line key={s} type="monotone" dataKey={`s${s}`} name={`shrinkage=${s}`} stroke={COLORS[i % COLORS.length]} dot />)}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
        <p className="mt-2 text-xs text-slate-500">Các siêu tham số còn lại giữ ở cấu hình tốt nhất. Lưu ý: cấu hình chốt nằm ở biên lưới (shrinkage lớn nhất) và bề mặt rất phẳng, nên chênh lệch giữa các cấu hình lân cận rất nhỏ.</p>
      </Card>

      {err.isLoading && <Spinner />}
      {err.error && <ErrorState error={err.error} retry={() => err.refetch()} />}
      {err.data && (
        <>
          <h2 className="text-lg font-semibold">Phân tích lỗi (test, KNNBaseline so với Bias-only)</h2>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <GroupChart title="Theo mức hoạt động của người dùng" rows={err.data.by_user_activity} />
            <GroupChart title="Theo độ phổ biến của phim (số rating train)" rows={err.data.by_item_popularity} />
            <GroupChart title="Theo điểm thật" rows={err.data.by_true_rating} />
          </div>
          <Card title="Theo số láng giềng thực dùng (KNNBaseline)">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500"><tr><th>Số láng giềng</th><th>Số cặp</th><th>RMSE</th><th>Sai số có dấu</th></tr></thead>
              <tbody>{err.data.by_n_neighbors.map((g) => <tr key={g.group} className="border-t border-slate-100"><td className="py-1">{g.group}</td><td>{g.n}</td><td className="font-mono">{f4(g.rmse_knn_baseline)}</td><td className="font-mono">{f4(g.bias_knn_baseline)}</td></tr>)}</tbody>
            </table>
          </Card>
          <Card title="10 dự đoán sai nặng nhất">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500"><tr><th>Phim</th><th>Thật</th><th>Dự đoán</th><th>Nguồn</th><th>Láng giềng</th><th>Rating train của phim</th></tr></thead>
              <tbody>{err.data.worst_10.map((w, i) => <tr key={i} className="border-t border-slate-100"><td className="py-1">{w.movie}</td><td>{w.rating}</td><td className="font-mono">{w.est.toFixed(2)}</td><td>{w.source}</td><td>{w.n_neighbors}</td><td>{w.item_train_n}</td></tr>)}</tbody>
            </table>
          </Card>
        </>
      )}

      <Card title="Giới hạn cần lưu ý">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
          <li>Dữ liệu MovieLens 100K thu thập 1997–1998, danh mục cũ; chia ngẫu nhiên theo người dùng đo khả năng khôi phục sở thích bị che, không phải dự báo tương lai.</li>
          <li>Phim giữ lại nghiêng về phim nhiều người chấm (thiên lệch phổ biến), nên mô hình phổ biến rất mạnh ở chỉ số xếp hạng; chênh lệch nhỏ giữa KNNBaseline và phổ biến chưa có khoảng tin cậy.</li>
          <li>Ngưỡng số rating tối thiểu của phim được chọn trên validation với ràng buộc giữ ≥ 25% danh mục làm ứng viên; test đã được chạy hai lần (trước và sau khi thêm ngưỡng).</li>
          <li>Phim chưa chấm không đồng nghĩa người dùng không thích; đánh giá offline không thay cho thử nghiệm với người dùng thật.</li>
        </ul>
      </Card>
    </div>
  )
}
