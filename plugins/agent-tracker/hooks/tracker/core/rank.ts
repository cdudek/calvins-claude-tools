import type { SessionRecord } from '../types'
import { completeCount } from './milestone'
import { cut } from './format'
import { UNTITLED } from './words'

const folder = (path: string) => path.replace(/\/+$/, '').split('/').pop() || path

const nameOf = (r: SessionRecord) => r.repo?.name ?? folder(r.cwd)
// A name of digits only (a scratch folder such as "5019") is no repo: it groups under "other".
export const isNumbered = (r: SessionRecord) => /^\d+$/.test(nameOf(r))
// The repo name, else the folder (a session in no repo is grouped by its folder).
export const repoLabel = (r: SessionRecord) => (isNumbered(r) ? 'other' : nameOf(r))
// "web-app/fix-login": the repo (cut to 12) and what the session is called.
export const sessionLabel = (r: SessionRecord) => `${cut(repoLabel(r), 12)}/${r.title ?? r.branch ?? UNTITLED}`

// A session the band counts: live in the list. A transcript record is history unless the list shows it: merge copies
// the list's status or state onto a record the list holds, and onto no other.
export const isLive = (r: SessionRecord) => r.state !== 'ended' && (r.source !== 'transcript' || r.engine.status !== undefined || r.engine.state !== undefined)

export type Line = { id: string; repo: string; title: string; ms: number | null; self: boolean; reason: SessionRecord['reason']; progress: { done: number; total: number } | null } // ms null: the wait is unknown

const lines = (sessions: SessionRecord[], state: SessionRecord['state'], selfId: string, now: number): Line[] =>
  sessions
    .filter(r => isLive(r) && r.state === state)
    .map(r => ({ id: r.sessionId, repo: repoLabel(r), title: r.title ?? UNTITLED, ms: r.engine.since === null ? null : Math.max(0, now - r.engine.since), self: r.sessionId === selfId, reason: r.reason, progress: r.milestone ? { done: completeCount(r.milestone.features), total: r.milestone.features.length } : null }))

// An unknown wait sorts after every known one.
const nullsLast = (a: Line, b: Line) => Number(a.ms === null) - Number(b.ms === null)
const longest = (a: Line, b: Line) => nullsLast(a, b) || (b.ms ?? 0) - (a.ms ?? 0) || a.id.localeCompare(b.id)

// Needs you: the one waiting longest first. Running: the one running longest first. Done: the latest first.
export const needsLines = (sessions: SessionRecord[], selfId: string, now: number) => lines(sessions, 'needs-you', selfId, now).sort(longest)
export const runningLines = (sessions: SessionRecord[], selfId: string, now: number) => lines(sessions, 'running', selfId, now).sort(longest)
export const doneLines = (sessions: SessionRecord[], selfId: string, now: number) => lines(sessions, 'done', selfId, now).sort((a, b) => nullsLast(a, b) || (a.ms ?? 0) - (b.ms ?? 0) || b.id.localeCompare(a.id))
