import type { SessionRecord } from '../types'
import { UNTITLED } from './words'

const folder = (path: string) => path.replace(/\/+$/, '').split('/').pop() || path

// The repo name, else the folder (a session in no repo is grouped by its folder).
export const repoLabel = (r: SessionRecord) => r.repo?.name ?? folder(r.cwd)

// A session the band counts: live in the list. A transcript-only record is history, never a count.
export const isLive = (r: SessionRecord) => r.state !== 'ended' && r.source !== 'transcript'

export type Line = { id: string; repo: string; title: string; ms: number; self: boolean }

const lines = (sessions: SessionRecord[], state: SessionRecord['state'], selfId: string, now: number): Line[] =>
  sessions
    .filter(r => isLive(r) && r.state === state)
    .map(r => ({ id: r.sessionId, repo: repoLabel(r), title: r.title ?? UNTITLED, ms: Math.max(0, now - r.engine.since), self: r.sessionId === selfId }))

const longest = (a: Line, b: Line) => b.ms - a.ms || a.id.localeCompare(b.id)

// Needs you: the one waiting longest first. Running: the one running longest first. Done: the latest first.
export const needsLines = (sessions: SessionRecord[], selfId: string, now: number) => lines(sessions, 'needs-you', selfId, now).sort(longest)
export const runningLines = (sessions: SessionRecord[], selfId: string, now: number) => lines(sessions, 'running', selfId, now).sort(longest)
export const doneLines = (sessions: SessionRecord[], selfId: string, now: number) => lines(sessions, 'done', selfId, now).sort((a, b) => longest(b, a))
