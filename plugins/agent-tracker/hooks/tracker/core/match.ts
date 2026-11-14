// What `/tracker session <text>` and `/tracker repo <text>` open (F122): a title or repo name by case-insensitive
// substring; for a session, else the id by prefix. Several matches open the most recent.
import type { SessionRecord } from '../types'
import { repoLabel } from './rank'

const recent = (r: SessionRecord) => Math.max(r.lastActivityAt, r.engine.since ?? 0)
const newest = (list: SessionRecord[]) => list.reduce<SessionRecord | null>((best, r) => (best === null || recent(r) > recent(best) || (recent(r) === recent(best) && r.sessionId < best.sessionId) ? r : best), null)

export const matchSession = (sessions: SessionRecord[], text: string): SessionRecord | null => {
  const t = text.trim().toLowerCase()
  if (t === '') return null
  const byTitle = sessions.filter(r => (r.title ?? '').toLowerCase().includes(t))
  return newest(byTitle.length > 0 ? byTitle : sessions.filter(r => r.sessionId.toLowerCase().startsWith(t)))
}

// The repo path of the most recent session in a repo whose name holds the text.
export const matchRepo = (sessions: SessionRecord[], text: string): string | null => {
  const t = text.trim().toLowerCase()
  if (t === '') return null
  return newest(sessions.filter(r => r.repo !== null && repoLabel(r).toLowerCase().includes(t)))?.repo?.path ?? null
}
