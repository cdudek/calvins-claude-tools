// The pane as plain data: what each page says (homeModel, ...) and how a row fits a width (rowLayout).
// Widths are terminal cells. Time and the local day are parameters: nothing here reads a clock.
import type { SessionRecord, Snapshot } from '../types'
import { duration, plural, tokens } from './format'
import { repoPrs } from './git'
import type { RepoPrs } from './git'
import { cells } from './band-model'
import { isLive, repoLabel } from './rank'
import { DETACHED, NEW_MARK, REASON_WORDS, THIS_SESSION, UNTITLED, moreLine, staleTop, updatedWords, withoutTracker } from './words'

export const WIDE = 70 // a row takes one line from here, two below
export const NARROW = 40 // below this the second line drops tokens, then the branch
export const DONE_MAX = 10
export const ENDED_MAX = 5

export type Page =
  | { kind: 'home' }
  | { kind: 'session'; id: string }
  | { kind: 'repo'; path: string }
  | { kind: 'missing'; what: 'session' | 'repo'; text: string }

// The day and the clock face are the I/O layer's: core never reads a time zone.
export type Local = { midnight: number; clock: (ms: number) => string }

// The cut title: "…" in place of the last cell.
export const cut = (text: string, max: number) => {
  const chars = [...text]
  return chars.length <= max ? text : max <= 1 ? '…' : `${chars.slice(0, max - 1).join('')}…`
}

export type PartTone = 'dim' | 'normal' | 'error'
export type PartKind = 'repo' | 'branch' | 'time' | 'reason' | 'tokens' | 'errors' | 'retries' | 'new'
export type Part = { kind: PartKind; text: string; tone: PartTone }
export type Row = { id: string; glyph: '●' | '◐' | '✓' | '○'; title: string; parts: Part[] }

const GLYPH = { 'needs-you': '●', running: '◐', done: '✓', ended: '○' } as const

const endedAt = (r: SessionRecord) => r.endedAt ?? r.lastActivityAt
const errors = (n: number) => `${n} ${n === 1 ? 'error' : 'errors'}`
const retries = (n: number) => `${n} ${n === 1 ? 'retry' : 'retries'}`

type Section = 'needs' | 'running' | 'done' | 'ended'

// One session as a row. Needs you shows the repo, the wait and the reason; the others show their time and numbers.
const rowOf = (r: SessionRecord, section: Section, now: number, selfId: string, isNew: boolean): Row => {
  const main: PartTone = section === 'needs' ? 'normal' : 'dim'
  const parts: Part[] = []
  const add = (kind: PartKind, text: string | null, tone: PartTone) => text !== null && text !== '' && parts.push({ kind, text, tone })
  if (section === 'needs') add('repo', repoLabel(r), 'dim')
  add('branch', r.branch ?? (r.repo ? DETACHED : null), 'dim')
  if (section === 'needs') add('time', duration(now - r.engine.since), main)
  if (section === 'running') add('time', duration(now - r.engine.since), main)
  if (section === 'done') add('time', `${duration(now - r.engine.since)} ago`, main)
  if (section === 'ended') add('time', `ended ${duration(now - endedAt(r))} ago`, main)
  if (section === 'needs') add('reason', REASON_WORDS[r.reason ?? 'waiting'], main)
  if (section !== 'needs') add('tokens', r.usage.tokensIn + r.usage.tokensOut > 0 ? `${tokens(r.usage.tokensIn + r.usage.tokensOut)} tokens` : null, 'dim')
  if (section !== 'ended') {
    add('errors', r.usage.toolErrors > 0 ? errors(r.usage.toolErrors) : null, main)
    add('retries', r.usage.retries > 0 ? retries(r.usage.retries) : null, main)
  }
  if (isNew) add('new', NEW_MARK, 'normal')
  const title = section === 'needs' && r.sessionId === selfId ? THIS_SESSION : (r.title ?? UNTITLED)
  return { id: r.sessionId, glyph: GLYPH[r.state], title, parts }
}

// How a row fits `columns`. Wide: one line, the title cut to leave the details whole. Narrow: the glyph and title, then
// a second line; below 40 columns that line drops tokens first, then the branch, until it fits.
export type RowLayout = { first: string; details: Part[]; inline: boolean }
export const rowLayout = (row: Row, columns: number): RowLayout => {
  const line = (parts: Part[]) => parts.map(p => p.text).join(' · ')
  if (columns >= WIDE) {
    const room = columns - 2 - 3 - cells(line(row.parts))
    return { first: `${row.glyph} ${cut(row.title, Math.max(1, room))}`, details: row.parts, inline: true }
  }
  let parts = row.parts
  const fits = () => 2 + cells(line(parts)) <= columns
  if (columns < NARROW) {
    if (!fits()) parts = parts.filter(p => p.kind !== 'tokens')
    if (!fits()) parts = parts.filter(p => p.kind !== 'branch')
  }
  return { first: `${row.glyph} ${cut(row.title, Math.max(1, columns - 2))}`, details: parts, inline: false }
}

// A repo heading: "web-app · 2 PRs · 1 failing". The counts show only where gh answered.
export type Group = { key: string; label: string; path: string | null; counts: string[]; rows: Row[] }
export const headingText = (g: { label: string; counts: string[] }, columns: number) => {
  const counts = g.counts.map(c => ` · ${c}`).join('')
  return `${cut(g.label, Math.max(1, columns - cells(counts)))}${counts}`
}

const prCounts = (sessions: SessionRecord[], path: string | null, now: number): string[] => {
  const p = path === null ? null : repoPrs(sessions, path, now)
  if (p === null || !p.ghOk) return []
  const failing = p.prs.filter(x => x.checks === 'failing').length
  return [...(p.prs.length > 0 ? [plural(p.prs.length, 'PR', 'PRs')] : []), ...(failing > 0 ? [`${failing} failing`] : [])]
}

// What Home keeps while the pane has the keyboard: the order of each section, and who already waited when the
// keyboard arrived (a newer one is marked new).
export type Frozen = { needs: string[]; running: string[]; done: string[]; ended: string[]; seenNeeds: string[] }

const inOrder = <T extends { sessionId: string }>(list: T[], order: string[] | undefined): T[] => {
  if (order === undefined) return list
  const at = (r: T) => order.indexOf(r.sessionId)
  const known = list.filter(r => at(r) >= 0).sort((a, b) => at(a) - at(b))
  return [...known, ...list.filter(r => at(r) < 0)]
}

// Sessions under repo headings, the group order that of its first session.
const grouped = (list: SessionRecord[], section: Section, sessions: SessionRecord[], now: number, selfId: string): Group[] => {
  const groups: Group[] = []
  for (const r of list) {
    const key = r.repo?.path ?? `folder:${r.cwd}`
    let g = groups.find(x => x.key === key)
    if (!g) groups.push((g = { key, label: repoLabel(r), path: r.repo?.path ?? null, counts: prCounts(sessions, r.repo?.path ?? null, now), rows: [] }))
    g.rows.push(rowOf(r, section, now, selfId, false))
  }
  return groups
}

export type RepoEntry = { path: string; label: string; counts: string[] }
export type HomeModel = {
  loading: boolean
  stale: string | null // the top line while the session list cannot be read (F123)
  partial: boolean // gh answered nothing
  withoutTracker: string | null
  updated: string
  alone: boolean // this is the only live session and it does not wait
  needs: Row[]
  running: Group[]
  done: Group[]
  doneMore: string | null
  ended: Row[]
  endedMore: string | null
  repos: RepoEntry[]
  frozen: Frozen
}

// Repos with a session in the last 7 days, the most recent first (F42).
export const repoEntries = (sessions: SessionRecord[], now: number): RepoEntry[] => {
  const latest = new Map<string, { label: string; at: number }>()
  for (const r of sessions) {
    if (!r.repo) continue
    const seen = latest.get(r.repo.path)
    const at = Math.max(r.lastActivityAt, r.endedAt ?? 0)
    if (!seen || at > seen.at) latest.set(r.repo.path, { label: repoLabel(r), at })
  }
  return [...latest.entries()].sort((a, b) => b[1].at - a[1].at || a[0].localeCompare(b[0])).map(([path, v]) => ({ path, label: v.label, counts: prCounts(sessions, path, now).slice(0, 1) }))
}

const sinceThenId = (a: SessionRecord, b: SessionRecord) => a.engine.since - b.engine.since || a.sessionId.localeCompare(b.sessionId)

export const homeModel = (snap: Snapshot, selfId: string, now: number, local: Local, frozen: Frozen | null): HomeModel => {
  const sessions = snap.sessions
  const live = sessions.filter(isLive)
  const of = (state: SessionRecord['state']) => live.filter(r => r.state === state)
  const alone = live.length === 1 && live[0]!.sessionId === selfId && live[0]!.state !== 'needs-you'

  const needsList = inOrder(of('needs-you').sort(sinceThenId), frozen?.needs)
  const seen = frozen?.seenNeeds
  const needs = needsList.map(r => rowOf(r, 'needs', now, selfId, seen !== undefined && !seen.includes(r.sessionId)))

  const runningList = alone ? [] : inOrder(of('running').sort(sinceThenId), frozen?.running)
  const doneAll = alone ? [] : inOrder(of('done').sort((a, b) => sinceThenId(b, a)), frozen?.done)
  const doneList = doneAll.slice(0, DONE_MAX)
  const endedAll = inOrder(
    sessions.filter(r => r.state === 'ended' && endedAt(r) >= local.midnight).sort((a, b) => endedAt(b) - endedAt(a) || a.sessionId.localeCompare(b.sessionId)),
    frozen?.ended,
  )
  const endedList = endedAll.slice(0, ENDED_MAX)

  const isStale = snap.at !== 0 && snap.failedReads >= 2
  const scanned = sessions.filter(r => r.repo).map(r => repoPrs(sessions, r.repo!.path, now)).filter((p): p is RepoPrs => p !== null)
  const lost = sessions.filter(r => r.source !== 'mod' && r.state !== 'ended').length

  return {
    loading: snap.at === 0,
    stale: isStale ? staleTop(snap.okAt > 0 ? duration(Math.max(0, now - snap.okAt)) : null) : null,
    partial: scanned.some(p => !p.ghOk),
    withoutTracker: lost > 0 ? withoutTracker(lost) : null,
    updated: updatedWords(duration(Math.max(0, now - snap.at))),
    alone,
    needs,
    running: grouped(runningList, 'running', sessions, now, selfId),
    done: grouped(doneList, 'done', sessions, now, selfId),
    doneMore: doneAll.length > DONE_MAX ? moreLine(doneAll.length - DONE_MAX) : null,
    ended: endedList.map(r => rowOf(r, 'ended', now, selfId, false)),
    endedMore: endedAll.length > ENDED_MAX ? moreLine(endedAll.length - ENDED_MAX) : null,
    repos: repoEntries(sessions, now),
    frozen: {
      needs: needsList.map(r => r.sessionId),
      running: runningList.map(r => r.sessionId),
      done: doneAll.map(r => r.sessionId),
      ended: endedAll.map(r => r.sessionId),
      seenNeeds: seen ?? needsList.map(r => r.sessionId),
    },
  }
}
