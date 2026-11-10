import { useState } from 'react'

/** Chấm 1–5 sao. Mỗi sao là một nút nên dùng được bằng bàn phím (Tab + Enter/Space). */
export function StarRating({
  value,
  onChange,
  onClear,
  disabled = false,
  size = 'md',
}: {
  value: number | null | undefined
  onChange: (rating: number) => void
  onClear?: () => void
  disabled?: boolean
  size?: 'sm' | 'md'
}) {
  const [hover, setHover] = useState<number | null>(null)
  const shown = hover ?? value ?? 0
  const px = size === 'sm' ? 'text-lg' : 'text-2xl'
  return (
    <div className="flex items-center gap-1" role="group" aria-label="Chấm điểm 1 đến 5 sao" onMouseLeave={() => setHover(null)}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          disabled={disabled}
          aria-label={`${n} sao`}
          aria-pressed={value === n}
          onMouseEnter={() => setHover(n)}
          onFocus={() => setHover(n)}
          onBlur={() => setHover(null)}
          onClick={() => onChange(n)}
          className={`${px} leading-none transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed ${n <= shown ? 'text-amber-400' : 'text-slate-300'}`}
        >
          ★
        </button>
      ))}
      {value != null && onClear && (
        <button type="button" disabled={disabled} onClick={onClear} className="ml-1 text-xs text-slate-500 underline hover:text-red-600" aria-label="Xóa điểm đã chấm">
          Xóa
        </button>
      )}
    </div>
  )
}
