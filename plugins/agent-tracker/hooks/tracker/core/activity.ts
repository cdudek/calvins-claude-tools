// When a session last did something, and when it started, in the words of the Session page. Pure: time comes in.
import type { SessionRecord } from '../types'
import type { Local } from './pane-model'

const DAY_MS = 24 * 60 * 60_000

// The newest of the last prompt, the last turn end (`lastActivityAt`) and the last line of the transcript (F71). A
// `lastActivityAt` equal to the start was set when the record was made, so it is no activity. null: none is known.
export const lastActivity = (r: Pick<SessionRecord, 'asks' | 'lastActivityAt' | 'startedAt'>, lastLine = 0): number | null => {
  const t = Math.max(r.lastActivityAt > r.startedAt ? r.lastActivityAt : 0, lastLine, ...r.asks.map(a => a.at))
  return t > 0 ? t : null
}

// "16:13" today, "Tue 16:13" up to 6 days back, "12 Sep 16:13" older, "12 Sep 2025 16:13" over a year (F6).
// shortcut: a week is counted in 24-hour days from local midnight, so a day with a clock change is an hour off, never a day.
export const startedWords = (at: number, now: number, local: Local): string =>
  at >= local.midnight ? local.clock(at) : `${at >= local.midnight - 6 * DAY_MS ? local.day(at) : local.date(at, now - at > 365 * DAY_MS)} ${local.clock(at)}`
