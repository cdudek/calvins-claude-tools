// What Clear on the Session page does, as plain data: when it is offered, what its confirm says, what the re-read at the press
// decides, the lines a run leaves. Pure: the list rows, the tasks and the clock face come in as parameters.
import type { AgentRow, Listing, SessionRecord, Snapshot } from '../types'
import { clean, cut, plural } from './format'
import type { TaskItem } from './tasks'
import { CLEAR_WORDS } from './words'

// A job id is a plain word: an id that is anything else (a leading "-" would read as a flag) never reaches `claude rm`.
const JOB_ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/
export const jobId = (id: string | undefined): string | null => (id !== undefined && JOB_ID.test(id) ? id : null)

// The rows of one good `claude agents --json` read, by session id: only what Clear needs (the job id and the process).
export const listingOf = (agents: AgentRow[]): Listing =>
  Object.fromEntries(agents.map(a => [a.sessionId, { ...(a.id !== undefined ? { id: a.id } : {}), ...(a.pid !== undefined ? { pid: a.pid } : {}) }]))
export const pidReported = (rows: Listing | AgentRow[] | undefined) => (Array.isArray(rows) ? rows : Object.values(rows ?? {})).some(a => a.pid !== undefined)

// The worktree a session ran in. Row 3 fills it from git (the five conditions); null: no linked worktree is known.
export type WorktreeFact = { label: string; branch: string | null; removable: boolean }

// What Clear would do: leave Claude Code's list (`id`: the job id of a listed row with no process), close the tasks Home lists for
// the session, and the worktree. A row with no job id is not listed as far as Clear goes: `claude rm` takes the job id.
export type ClearWork = { id: string | null; tasks: TaskItem[]; worktree: WorktreeFact | null }

// `left`: `claude rm` already worked on this visit, so the snapshot's row is out of date until the next read.
export const workOf = (r: SessionRecord, snap: Snapshot, tasks: TaskItem[], worktree: WorktreeFact | null, left = false): ClearWork => {
  const row = snap.listing?.[r.sessionId]
  return { id: left || row === undefined || row.pid !== undefined ? null : jobId(row.id), tasks: r.source === 'transcript' ? [] : tasks.filter(t => t.sessionId === r.sessionId), worktree }
}

export type Gate = 'live' | 'unreadable' | 'pid-unknown' | 'nothing' | 'clear'

// Whether Clear is drawn, and if not, which line takes its place. A session with a process is never cleared (F9); a list that
// could not be read twice, or that names no process at all, says nothing about whether a process runs (F11, F12).
export const clearGate = (r: SessionRecord, snap: Snapshot, work: ClearWork): Gate => {
  if (r.state !== 'ended') return 'live'
  if (snap.failedReads >= 2) return 'unreadable'
  if (!pidReported(snap.listing)) return 'pid-unknown'
  return work.id !== null || work.tasks.length > 0 || work.worktree?.removable === true ? 'clear' : 'nothing'
}

// ---- the confirm ----

// The lines under "Clear this session?", from the parts that apply, in this order.
export const confirmLines = (w: ClearWork): string[] => {
  const n = w.tasks.length
  const closes = `the ${plural(n, 'task', 'tasks')} above`
  const kept = [w.id !== null ? CLEAR_WORDS.kept : '', n > 0 ? CLEAR_WORDS.reopenHint : ''].filter(x => x !== '').join(' ')
  return [
    w.id !== null ? `${CLEAR_WORDS.leaves}${n > 0 ? ` and closes ${closes}` : ''}.` : n > 0 ? `It closes ${closes}.` : '',
    w.id !== null && w.worktree !== null ? CLEAR_WORDS.madeWorktree(w.worktree.label) : '',
    kept,
  ].filter(l => l !== '')
}

// ---- the press ----

// Why nothing was changed, or what a run did. `closed` are the task keys it closed, for Reopen tasks.
export type Outcome =
  | { kind: 'running' }
  | { kind: 'unreadable' }
  | { kind: 'no-pid' }
  | { kind: 'failed'; reason: string }
  | { kind: 'partly'; reason: string; left: boolean }
  | { kind: 'cleared'; left: boolean; closed: string[] }
  | { kind: 'reopened'; count: number }

// The page's own state for one visit: the confirm, the run, the lines it left. `left` stays true once `claude rm` worked.
export type ClearState = { step: 'idle' | 'confirm' | 'clearing'; left: boolean; outcome: Outcome | null }
export const IDLE: ClearState = { step: 'idle', left: false, outcome: null }

// What the read at the press says to do. A session with a process, a read that failed or one that names no process at all
// refuses and changes nothing; a listed row with a job id and no process is removed; anything else is not listed.
export type Step = { do: 'refuse'; outcome: Outcome } | { do: 'rm'; id: string } | { do: 'skip' }
export const decide = (rows: AgentRow[] | null, sessionId: string): Step => {
  if (rows === null) return { do: 'refuse', outcome: { kind: 'unreadable' } }
  const row = rows.find(a => a.sessionId === sessionId)
  if (row?.pid !== undefined) return { do: 'refuse', outcome: { kind: 'running' } }
  if (!pidReported(rows)) return { do: 'refuse', outcome: { kind: 'no-pid' } }
  const id = jobId(row?.id)
  return id === null ? { do: 'skip' } : { do: 'rm', id }
}

// What a command printed, as one short line for an error: no escape sequences, the first line with words, cut at 60 cells.
// An empty answer gives "": the clause is dropped.
export const reasonOf = (printed: string | undefined): string => {
  const first = clean((printed ?? '').replace(/\x1b\[[0-9;?]*[A-Za-z]/g, ''), 400).split('\n').map(l => l.trim()).find(l => l !== '') ?? ''
  return cut(first.replace(/\.$/, ''), 60)
}

// The lines of an outcome, as the result block draws them: [glyph, words] where the glyph is "✓", "✗" or none.
export type ResultLine = { glyph: '✓' | '✗' | null; text: string }
export const outcomeLines = (o: Outcome): ResultLine[] => {
  const why = (r: string) => (r === '' ? '' : `: ${r}`)
  switch (o.kind) {
    case 'running':
      return [{ glyph: null, text: CLEAR_WORDS.refusedRunning }]
    case 'unreadable':
      return [{ glyph: null, text: CLEAR_WORDS.refusedUnreadable }]
    case 'no-pid':
      return [{ glyph: null, text: CLEAR_WORDS.refusedNoPid }]
    case 'failed':
      return [{ glyph: '✗', text: CLEAR_WORDS.failed(why(o.reason)) }]
    case 'partly':
      return [{ glyph: '✗', text: CLEAR_WORDS.partly(why(o.reason), o.left) }]
    case 'cleared':
      return [...(o.left ? [{ glyph: '✓' as const, text: CLEAR_WORDS.left }] : []), ...(o.closed.length > 0 ? [{ glyph: '✓' as const, text: CLEAR_WORDS.closed(o.closed.length) }] : [])]
    case 'reopened':
      return [{ glyph: '✓', text: CLEAR_WORDS.reopened(o.count) }]
  }
}
