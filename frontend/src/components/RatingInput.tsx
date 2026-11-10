import { useState } from 'react'

/** Rate 1–5 with five numbered cells, filled up to the chosen value. Every cell is a button, so it works with the keyboard. */
export function RatingInput({
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
  return (
    <div className="flex items-center gap-2" onMouseLeave={() => setHover(null)}>
      <div className={`rate ${size === 'sm' ? 'rate-sm' : ''}`} role="group" aria-label="Rate from 1 to 5">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            className="rate-cell"
            data-on={n <= shown}
            disabled={disabled}
            aria-label={`Rate ${n} out of 5`}
            aria-pressed={value === n}
            onMouseEnter={() => setHover(n)}
            onFocus={() => setHover(n)}
            onBlur={() => setHover(null)}
            onClick={() => onChange(n)}
          >
            {n}
          </button>
        ))}
      </div>
      {value != null && onClear && (
        <button type="button" disabled={disabled} onClick={onClear} className="micro underline hover:text-alert" aria-label="Clear my rating">
          Clear
        </button>
      )}
    </div>
  )
}
