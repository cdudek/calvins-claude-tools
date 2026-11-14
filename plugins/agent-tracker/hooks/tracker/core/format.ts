// Durations as the tracker writes them, to the minute (F125): "<1m", "6m", "2h 10m", "3d".
export const duration = (ms: number) => {
  const m = Math.floor(Math.max(0, ms) / 60_000)
  if (m < 1) return '<1m'
  if (m < 60) return `${m}m`
  if (m < 24 * 60) return m % 60 === 0 ? `${m / 60}h` : `${Math.floor(m / 60)}h ${m % 60}m`
  return `${Math.floor(m / (24 * 60))}d`
}

export const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

// Tokens as the pane writes them: "950", "12k", "41k", "1.2M".
export const tokens = (n: number) => (n < 1000 ? String(n) : n < 1_000_000 ? `${Math.round(n / 1000)}k` : `${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`)
