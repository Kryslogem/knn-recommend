import { useEffect } from 'react'
import type { RecItem } from '../api/types'
import { Button, SourceBadge } from './ui'

const sign = (x: number) => `${x >= 0 ? '+' : '−'}${Math.abs(x).toFixed(2)}`

/** Giải thích một đề xuất: nguồn, số láng giềng thực dùng và phân rã điểm μ + b_user + b_item + phần láng giềng. */
export function ExplainDrawer({ item, onClose }: { item: RecItem; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const b = item.breakdown
  const parts = b
    ? [
        { key: 'μ', label: 'Điểm trung bình toàn hệ thống', v: b.mu, base: true },
        { key: 'b_user', label: 'Xu hướng chấm điểm của bạn', v: b.b_user },
        { key: 'b_item', label: 'Độ nổi trội của phim', v: b.b_item },
        { key: 'KNN', label: `Phần điều chỉnh từ ${item.n_neighbors} người có gu giống bạn`, v: b.neighbor_term },
      ]
    : []
  const maxSim = Math.max(...item.neighbors.map((n) => n.similarity), 1e-9)
  const maxAbs = Math.max(...parts.map((p) => Math.abs(p.v)), 1)

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/30" onClick={onClose}>
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`Vì sao đề xuất ${item.movie.title}`}
        className="h-full w-full max-w-md overflow-y-auto bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">{item.movie.title}</h2>
            <p className="text-sm text-slate-500">{item.movie.genres.join(' · ')}</p>
          </div>
          <Button variant="ghost" onClick={onClose} aria-label="Đóng">
            ✕
          </Button>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <span className="text-3xl font-bold text-indigo-700">{item.predicted_rating.toFixed(2)}</span>
          <div>
            <p className="text-xs text-slate-500">điểm dự đoán cho bạn (1–5)</p>
            <SourceBadge source={item.source} />
          </div>
        </div>

        {item.source === 'knn' && <p className="mt-3 text-sm text-slate-700">Dựa trên <b>{item.n_neighbors}</b> người xem có gu giống bạn đã chấm phim này.</p>}
        {item.source === 'baseline' && <p className="mt-3 text-sm text-slate-700">Chưa đủ người có gu giống bạn đã chấm phim này ({item.n_neighbors} người), nên điểm chỉ dựa trên điểm nền.</p>}
        {item.source === 'popular' && <p className="mt-3 text-sm text-slate-700">Bạn chưa chấm phim nào mà hệ thống biết, nên đây là phim được nhiều người chấm cao. Hãy chấm vài phim để nhận đề xuất cá nhân hóa.</p>}

        {b && (
          <div className="mt-5">
            <h3 className="mb-2 text-sm font-semibold text-slate-800">Điểm được tạo thành như thế nào</h3>
            <ul className="space-y-2">
              {parts.map((p) => (
                <li key={p.key}>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-700">
                      <code className="rounded bg-slate-100 px-1">{p.key}</code> {p.label}
                    </span>
                    <span className="font-mono">{p.base ? p.v.toFixed(2) : sign(p.v)}</span>
                  </div>
                  <div className="mt-1 h-1.5 rounded bg-slate-100">
                    <div
                      className={`h-1.5 rounded ${p.base ? 'bg-slate-400' : p.v >= 0 ? 'bg-emerald-500' : 'bg-red-400'}`}
                      style={{ width: `${Math.min(100, (Math.abs(p.v) / maxAbs) * 100)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
            {b.clipped && <p className="mt-2 text-xs text-slate-500">Tổng vượt khoảng 1–5 nên được cắt về giới hạn.</p>}
          </div>
        )}

        {item.neighbors.length > 0 && (
          <div className="mt-5">
            <h3 className="mb-2 text-sm font-semibold text-slate-800">Những người ảnh hưởng nhiều nhất (ẩn danh)</h3>
            <ul className="space-y-2 text-sm">
              {item.neighbors.map((n) => (
                <li key={n.label} className="rounded border border-slate-200 p-2">
                  <div className="flex justify-between">
                    <span>{n.label}</span>
                    <span>
                      chấm <b>{n.rating}★</b>
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500" title={`Độ tương đồng gốc: ${n.similarity}`}>
                    Giống bạn ~{Math.round((n.similarity / maxSim) * 100)}% (so với người giống nhất) · {n.common_items} phim chung
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        <p className="mt-5 rounded bg-slate-50 p-3 text-xs text-slate-500">
          Lưu ý: điểm dự đoán là ước lượng điểm bạn có thể chấm, <b>không phải xác suất bạn sẽ thích</b>. Phim chưa chấm không có nghĩa là bạn chưa xem.
        </p>
      </aside>
    </div>
  )
}
