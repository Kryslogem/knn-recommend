// Shared chart styling: ink and hazard red only, no rounded corners, monospace type.
export const INK = '#111111'
export const ALERT = '#e61919'
export const MUTED = '#8a8a84'
export const GRID_STROKE = 'rgba(17,17,17,0.18)'
// Line series are told apart by dash pattern as well as colour (works in greyscale prints).
export const SERIES: { stroke: string; dash?: string }[] = [
  { stroke: INK },
  { stroke: ALERT },
  { stroke: INK, dash: '8 4' },
  { stroke: MUTED },
  { stroke: INK, dash: '2 4' },
  { stroke: ALERT, dash: '8 4' },
]
export const TOOLTIP_STYLE = {
  border: `2px solid ${INK}`,
  background: '#f4f4f0',
  borderRadius: 0,
  fontFamily: '"JetBrains Mono", monospace',
  fontSize: 11,
  textTransform: 'uppercase' as const,
}
