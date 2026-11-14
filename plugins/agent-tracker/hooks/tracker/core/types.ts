import type { SessionRecord } from '../types'

export const MODEL = 'haiku' // the one model constant: every model call pins it (F60)
// The `waitingFor` a permission prompt reports. None was recorded at build (questions.md Q1), so "asks permission"
// never shows and any waitingFor gives "waiting" (F4). Set it from a recorded permission wait.
export const PERMISSION_WAITING_FOR: string | null = null
export const POLL_MS = 5000
export const REDRAW_MS = 60_000 // the band and the pane redraw once a minute, so the times stay true (F126)
export const PANE_ID = 'tracker' // the pane the band's Pane button opens; feature 4 draws it
export const LEASE_FRESH_MS = 15_000
// Raised when the lease holder gains a duty an older tracker does not run (2: the late check). A newer tracker takes the lease
// from an older holder, which yields on its next poll, so one old session left open never blocks a new duty.
export const LEASE_GEN = 2
export const WEEK_MS = 7 * 24 * 3600 * 1000
export const ASKS_MAX = 200
export const ASK_TEXT_MAX = 2000

export const emptyRecord = (sessionId: string, cwd: string, now: number): SessionRecord => ({
  v: 1,
  sessionId,
  source: 'mod',
  writtenAt: now,
  kind: 'interactive',
  title: null,
  cwd,
  repo: null,
  branch: null,
  startedAt: now,
  lastActivityAt: now,
  endedAt: null,
  engine: { since: now },
  state: 'running',
  reason: null,
  unknownValue: null,
  questionFlag: null,
  usage: { tokensIn: 0, tokensOut: 0, toolErrors: 0, retries: 0 },
  asks: [],
  runs: { goalSince: null, subagents: [], background: [] },
  milestone: null,
  scan: null,
})
