import { useEffect } from 'react'
import type { RecItem } from '../api/types'
import { Button, SourceBadge } from './ui'

const sign = (x: number) => `${x >= 0 ? '+' : '-'}${Math.abs(x).toFixed(2)}`

/** Explains one recommendation: source, neighbours actually used, and the score breakdown mu + b_user + b_item + neighbour term. */
export function ExplainDrawer({ item, onClose }: { item: RecItem; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const b = item.breakdown
  const parts = b
    ? [
        { key: 'mu', label: 'Global average rating', v: b.mu, base: true },
        { key: 'b_user', label: 'How generously you rate', v: b.b_user },
        { key: 'b_item', label: 'How well this film is rated overall', v: b.b_item },
        { key: 'KNN', label: `Adjustment from ${item.n_neighbors} similar viewers`, v: b.neighbor_term },
      ]
    : []
  const maxSim = Math.max(...item.neighbors.map((n) => n.similarity), 1e-9)
  const maxAbs = Math.max(...parts.map((p) => Math.abs(p.v)), 1)

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-ink/50" onClick={onClose}>
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`Why ${item.movie.title} was recommended`}
        className="h-full w-full max-w-md overflow-y-auto border-l-4 border-ink bg-paper"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b-2 border-ink bg-ink p-4 text-paper">
          <div>
            <p className="micro opacity-70">Explanation / film {String(item.movie.id).padStart(4, '0')}</p>
            <h2 className="display mt-2 text-xl">{item.movie.title}</h2>
            <p className="micro mt-1">{item.movie.genres.join(' / ')}</p>
          </div>
          <button className="btn btn-sm" style={{ color: 'var(--color-paper)', borderColor: 'var(--color-paper)', background: 'transparent' }} onClick={onClose} aria-label="Close">
            Close [esc]
          </button>
        </div>

        <div className="space-y-5 p-4">
          <div className="flex items-end gap-4">
            <span className="display num text-6xl">{item.predicted_rating.toFixed(2)}</span>
            <div className="pb-1">
              <p className="micro">Predicted rating (1-5)</p>
              <div className="mt-1">
                <SourceBadge source={item.source} />
              </div>
            </div>
          </div>

          {item.source === 'knn' && (
            <p>
              Based on <b>{item.n_neighbors}</b> viewers with similar taste who have rated this film.
            </p>
          )}
          {item.source === 'baseline' && (
            <p>Only {item.n_neighbors} similar viewers have rated this film, which is too few, so the score uses the baseline only.</p>
          )}
          {item.source === 'popular' && <p>You have not rated any film the system knows yet, so this is a popular pick. Rate a few films to get personalized results.</p>}

          {b && (
            <div>
              <h3 className="h-sec mb-3 !text-base">How the score is built</h3>
              <ul className="ruled">
                {parts.map((p) => (
                  <li key={p.key} className="p-3">
                    <div className="flex justify-between gap-3">
                      <span>
                        <span className="tag mr-2">{p.key}</span>
                        {p.label}
                      </span>
                      <span className="num font-bold">{p.base ? p.v.toFixed(2) : sign(p.v)}</span>
                    </div>
                    <div className="mt-2 h-2 border-2 border-ink">
                      <div className={`h-full ${p.base ? 'bg-ink/40' : p.v >= 0 ? 'bg-ink' : 'bg-alert'}`} style={{ width: `${Math.min(100, (Math.abs(p.v) / maxAbs) * 100)}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
              {b.clipped && <p className="micro mt-2">Total is outside 1-5 and was clamped to the limit.</p>}
            </div>
          )}

          {item.neighbors.length > 0 && (
            <div>
              <h3 className="h-sec mb-3 !text-base">Most influential viewers (anonymous)</h3>
              <ul className="ruled">
                {item.neighbors.map((n) => (
                  <li key={n.label} className="p-3" title={`Raw similarity: ${n.similarity}`}>
                    <div className="flex justify-between">
                      <span className="font-bold">{n.label}</span>
                      <span>
                        rated <b>{n.rating}/5</b>
                      </span>
                    </div>
                    <p className="micro num mt-1">
                      {Math.round((n.similarity / maxSim) * 100)}% as similar as your closest match · {n.common_items} films in common
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="border-2 border-ink p-3 micro leading-relaxed">
            Note: the predicted rating estimates the score you might give. It is <b>not</b> the probability that you will like the film. A film you have not rated is not necessarily a film you have not seen.
          </p>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
      </aside>
    </div>
  )
}
