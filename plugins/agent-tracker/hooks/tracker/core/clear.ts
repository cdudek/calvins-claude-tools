// What Clear on the Session page does, as plain data: when it is offered, what its confirm says, what the re-read at the press
// decides, the lines a run leaves. Pure: the list rows, the tasks and the clock face come in as parameters.
import type { AgentRow, Listing, SessionRecord, Snapshot } from '../types'
import { clean, cut, plural } from './format'
import type { TaskItem } from './tasks'
import type { Facts, WorktreeFact } from './worktree'
import { CLEAR_WORDS, WORKTREE_WORDS } from './words'

// A job id is a plain word: an id that is anything else (a leading "-" would read as a flag) never reaches `claude rm`.
const JOB_ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/
export const jobId = (id: string | undefined): string | null => (id !== undefined && JOB_ID.test(id) ? id : null)

// The rows of one good `claude agents --json` read, by session id: only what Clear needs (the job id and the process).
export const listingOf = (agents: AgentRow[]): Listing =>
  Object.fromEntries(agents.map(a => [a.sessionId, { ...(a.id !== undefined ? { id: a.id } : {}), ...(a.pid !== undefined ? { pid: a.pid } : {}) }]))
export const pidReported = (rows: Listing | AgentRow[] | undefined) => (Array.isArray(rows) ? rows : Object.values(rows ?? {})).some(a => a.pid !== undefined)

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
export const hasProcess = (r: SessionRecord, snap: Snapshot) => r.state !== 'ended' || snap.listing?.[r.sessionId]?.pid !== undefined

export const clearGate = (r: SessionRecord, snap: Snapshot, work: ClearWork): Gate => {
  if (snap.listing?.[r.sessionId]?.pid !== undefined) return 'live'
  if (snap.failedReads >= 2) return 'unreadable'
  if (!pidReported(snap.listing)) return 'pid-unknown' // before the record's state: with no pid in the read nothing says the state is true (F11)
  if (hasProcess(r, snap)) return 'live'
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

// What the worktree offer did, as lines: removed (F43), removed by Claude Code (F46), a condition changed at the press (F44) or
// git refused (F45). `why` is the reason clause, ": reason" or "".
export type WtOutcome =
  | { kind: 'removed'; label: string; branch: string | null }
  | { kind: 'claude-removed'; label: string }
  | { kind: 'changed'; why: string }
  | { kind: 'refused'; why: string }

// What git said about the session's folder, read when the page opened for this session (`id`) in this state (`ended`), and again
// after the steps that can change it. `value` null: no linked worktree, or git could not say. `reading`: the first read is running.
export type Read = { id: string; ended: boolean; value: Facts | null; reading: boolean }

// The page's own state for one visit: the confirm, the run, the lines it left, the worktree offer. `left` stays true once `claude rm`
// worked. `offer`: the owner can remove the worktree now; `wt`: what the offer did.
export type ClearState = { step: 'idle' | 'confirm' | 'clearing' | 'removing'; left: boolean; outcome: Outcome | null; offer: boolean; wt: WtOutcome | null; facts: Read | null }
export const IDLE: ClearState = { step: 'idle', left: false, outcome: null, offer: false, wt: null, facts: null }

// Only the worktree is left to clear: Clear opens the offer, which is its own confirm (F21).
export const onlyWorktree = (w: ClearWork) => w.id === null && w.tasks.length === 0 && w.worktree?.removable === true

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

export const wtLines = (o: WtOutcome): ResultLine[] => {
  switch (o.kind) {
    case 'removed':
      return [{ glyph: '✓', text: WORKTREE_WORDS.removed(o.label, o.branch) }, { glyph: null, text: WORKTREE_WORDS.resume }]
    case 'claude-removed':
      return [{ glyph: '✓', text: WORKTREE_WORDS.claudeRemoved(o.label) }, { glyph: null, text: WORKTREE_WORDS.resume }]
    case 'changed':
      return [{ glyph: '✗', text: WORKTREE_WORDS.changed(o.why) }]
    case 'refused':
      return [{ glyph: '✗', text: WORKTREE_WORDS.gitFailed(o.why === '' ? '' : `: ${o.why}`) }]
  }
}
