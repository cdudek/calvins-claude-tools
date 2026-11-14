// "Your tasks not done": the task asks nobody has finished, each with one status, from the session's record, its PR and the
// owner's marks. Pure: time and the marks are parameters; the pane, the band and the Board draw what this returns.
import type { Ask, SessionRecord, Snapshot } from '../types'
import { clean, duration } from './format'
import { repoPrs } from './git'
import { completeCount } from './milestone'
import { repoLabel } from './rank'
import { WEEK_MS } from './types'

export const IDLE_MS = 30 * 60_000 // the owner chose 30: a session quiet for longer than this, with a task not done, is forgotten
export const TASK_TEXT_MAX = 600

export type TaskStatus = 'needs-you' | 'forgotten' | 'superseded' | 'in-progress'
export const TASK_ORDER: TaskStatus[] = ['needs-you', 'forgotten', 'superseded', 'in-progress']
export const TASK_LABEL = { 'needs-you': 'You', forgotten: 'Forgotten', superseded: 'Superseded?', 'in-progress': 'In progress' } as const

export type TaskItem = {
  key: string // `<session>:<ask n>`, what Keep and Close are kept under
  sessionId: string
  n: number
  text: string
  repo: string
  at: number // when it was asked
  status: TaskStatus
  detail: string // the words after the label: "session ended 2h ago, not done"; empty for a superseded task, which shows `later`
  later: { at: number; text: string } | null // the ask that may have replaced it
  progress: { slug: string; done: number; total: number } | null // the milestone, for a task in progress
}

// What the owner and the repos say: Keep and Close from settings.json, and `<repo path>|<branch>` of each merged change.
export type TaskMarks = { kept: ReadonlySet<string>; closed: ReadonlySet<string>; merged: ReadonlySet<string> }
export const noMarks: TaskMarks = { kept: new Set(), closed: new Set(), merged: new Set() }

export const taskKey = (sessionId: string, n: number) => `${sessionId}:${n}`
export const mergedKey = (repoPath: string, branch: string) => `${repoPath}|${branch}`

// The first words of an ask, for the line that names the later one.
export const firstWords = (text: string, words = 5) => {
  const all = text.replace(/\s+/g, ' ').trim().split(' ')
  return all.length > words ? `${all.slice(0, words).join(' ')}…` : all.join(' ')
}

// One task ask's status, first match wins; null: done (not on the list). `hasPr`: an open PR is on the session's branch.
export const taskStatus = (r: SessionRecord, a: Ask, now: number, marks: TaskMarks, hasPr: boolean): Pick<TaskItem, 'status' | 'detail' | 'later' | 'progress'> | null => {
  const key = taskKey(r.sessionId, a.n)
  const isMerged = r.repo !== null && r.branch !== null && marks.merged.has(mergedKey(r.repo.path, r.branch))
  if (a.verdict === 'done' || isMerged || marks.closed.has(key)) return null
  const none = { later: null, progress: null }
  if (r.state === 'needs-you' && a.n === r.asks[r.asks.length - 1]?.n) {
    return { status: 'needs-you', detail: `waiting for your answer${r.engine.since === null ? '' : ` for ${duration(now - r.engine.since)}`}`, ...none }
  }
  const ended = r.state === 'ended'
  // A running session is working, whatever its last prompt or turn says: only a quiet one is idle.
  if (ended || (r.state !== 'running' && now - r.lastActivityAt > IDLE_MS)) {
    const why = ended ? `session ended ${duration(now - (r.endedAt ?? r.lastActivityAt))} ago, not done` : `idle ${duration(now - r.lastActivityAt)}, not done`
    return { status: 'forgotten', detail: r.milestone === null && !hasPr ? `${why}, no milestone, no PR` : why, ...none }
  }
  if (a.verdict === 'replaced' && !marks.kept.has(key)) {
    const later = r.asks.find(x => x.n === a.replacedBy)
    return { status: 'superseded', detail: '', later: later ? { at: later.at, text: firstWords(later.text) } : null, progress: null }
  }
  const m = r.milestone
  return { status: 'in-progress', detail: '', later: null, progress: m ? { slug: m.slug, done: completeCount(m.features), total: m.features.length } : null }
}

// Every task ask of the last week that is not done: needs you, forgotten, superseded, in progress; newest first inside each.
export const taskItems = (snap: Snapshot, now: number, marks: TaskMarks = noMarks): TaskItem[] => {
  const out: TaskItem[] = []
  for (const r of snap.sessions) {
    const hasPr = r.repo !== null && r.branch !== null && (repoPrs(snap.sessions, r.repo.path, now)?.prs.some(p => p.branch === r.branch) ?? false)
    for (const a of r.asks) {
      if (a.kind !== 'task' || a.at < now - WEEK_MS) continue
      const s = taskStatus(r, a, now, marks, hasPr)
      if (s !== null) out.push({ key: taskKey(r.sessionId, a.n), sessionId: r.sessionId, n: a.n, text: clean(a.text, TASK_TEXT_MAX).replace(/\s+/g, ' ').trim(), repo: repoLabel(r), at: a.at, ...s })
    }
  }
  return out.sort((a, b) => TASK_ORDER.indexOf(a.status) - TASK_ORDER.indexOf(b.status) || b.at - a.at || a.key.localeCompare(b.key))
}

// The count the band shows, and whether it is red: a forgotten task or one waiting for you.
export const taskCounts = (items: TaskItem[]) => ({ notDone: items.length, needsYou: items.filter(t => t.status === 'needs-you').length, alarm: items.some(t => t.status === 'needs-you' || t.status === 'forgotten') })

// ---- the verdicts haiku gives at turn.complete ----

export const openTaskAsks = (asks: Ask[]) => asks.filter(a => a.kind === 'task' && a.verdict !== 'done')

export type Judged = { n: number; verdict: NonNullable<Ask['verdict']>; by?: number }
export const applyVerdicts = (asks: Ask[], judged: Judged[]): Ask[] =>
  asks.map(a => {
    const j = a.kind === 'task' ? judged.find(x => x.n === a.n) : undefined
    if (j === undefined) return a
    const { replacedBy: _old, ...rest } = a
    return { ...rest, verdict: j.verdict, ...(j.verdict === 'replaced' && j.by !== undefined ? { replacedBy: j.by } : {}) }
  })
