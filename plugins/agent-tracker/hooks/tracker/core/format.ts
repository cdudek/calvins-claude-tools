// Durations as the tracker writes them, to the minute (F125): "<1m", "6m", "2h 10m", "3d".
export const duration = (ms: number) => {
  const m = Math.floor(Math.max(0, ms) / 60_000)
  if (m < 1) return '<1m'
  if (m < 60) return `${m}m`
  if (m < 24 * 60) return m % 60 === 0 ? `${m / 60}h` : `${Math.floor(m / 60)}h ${m % 60}m`
  return `${Math.floor(m / (24 * 60))}d`
}
