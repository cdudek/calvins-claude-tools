// The pane as plain data, as the owner's mockups draw it (2026-11-14): every page is a PaneModel, a header, then blocks of
// coloured lines, rows that are Buttons and inline lists. Time and the local day are parameters: nothing here reads a clock.
// Widths are terminal cells.
import type { SessionRecord, Snapshot } from '../types'
import { cells, cut, duration, pad } from './format'
import { prsOf } from './band-model'
import { isLive, repoLabel } from './rank'
import { completeCount } from './milestone'
import { bar, dim, DOT, join, percent, sp } from './paint'
import type { Span, Spans } from './paint'
import { HEADINGS, NOTHING_NEEDS, ONLY_THIS, NO_REPOS, NEW_MARK, PRS_NOT_SHOWN, THIS_SESSION, UNTITLED, KEY_HINTS, moreLine, staleTop, updatedWords, withoutTracker } from './words'

export const GROUP_MAX = 12 // a long repo name gives way to the session's own name
export const RUN_MAX = 8 // Running rows on Home before "and N more"
export const REPOS_MAX = 8

export type Page =
  | { kind: 'home' }
  | { kind: 'session'; id: string }
  | { kind: 'repo'; path: string }
  | { kind: 'milestone'; repo: string; change: string }
  | { kind: 'feature'; repo: string; change: string; n: number }
  | { kind: 'missing'; what: 'session' | 'repo'; text: string }

// The day and the clock face are the I/O layer's: core never reads a time zone. `day` is the weekday of an older ask.
export type Local = { midnight: number; clock: (ms: number) => string; day: (ms: number) => string }

// One item of an inline list: a Button when it has `to`, a Link when it has `href`, plain text otherwise.
export type Item = { key: string; spans: Spans; to?: Page; href?: string; joined?: boolean } // joined: no separator before it
export type Block =
  | { kind: 'lines'; key: string; lines: Spans[]; wrap?: boolean }
  | { kind: 'rule' }
  | { kind: 'row'; key: string; to: Page; lines: Spans[] }
  | { kind: 'inline'; key: string; head: Spans; items: Item[]; sep: Span | null }
  | { kind: 'copy'; key: string; label: string }

// The breadcrumb: every crumb with a page is a Button; the last is the page itself.
export type Crumb = { text: string; to: Page | null; bold?: boolean }
export type PaneModel = { crumbs: Crumb[]; right: Spans; blocks: Block[]; footer: Spans | null; first: string | null }

export const rowsOf = (blocks: Block[]) => blocks.flatMap(b => (b.kind === 'row' || b.kind === 'copy' || b.kind === 'inline' ? [b] : []))
// The key a page's focus ring starts on: its first row, else the first item of its first inline list.
export const firstKey = (blocks: Block[]): string | null => {
  for (const b of blocks) {
    if (b.kind === 'row' || b.kind === 'copy') return b.key
    if (b.kind === 'inline') {
      const item = b.items.find(i => i.to !== undefined)
      if (item) return item.key
    }
  }
  return null
}

// No rule twice in a row, none at the end.
export const tidy = (blocks: Block[]): Block[] => blocks.filter((b, i, all) => !(b.kind === 'rule' && (all[i - 1]?.kind === 'rule' || i === all.length - 1)))

export const hint = (extra: string | null = null): Spans => [dim(`${KEY_HINTS}${extra === null ? '' : ` · ${extra}`}`)]
export const heading = (text: string, tone?: Span['tone'], extra: Spans = []): Spans => [sp(text, tone, { bold: true }), ...extra]
export const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))

// ---- names ----

const folder = (path: string) => path.replace(/\/+$/, '').split('/').pop() || path

// Where a session belongs: its repo; a folder named by number only is no repo, so it goes under the repo that holds it, or "other".
export const groupName = (r: SessionRecord, sessions: SessionRecord[]): string => {
  if (r.repo) return repoLabel(r)
  const name = folder(r.cwd)
  if (!/^\d+$/.test(name)) return name
  const holder = sessions.find(x => x.repo !== null && (r.cwd === x.repo.path || r.cwd.startsWith(`${x.repo.path}/`)))
  return holder ? repoLabel(holder) : 'other'
}

// "web-app/fix-login": the group and what the session is called; this session says so when it waits.
export const rowLabel = (r: SessionRecord, sessions: SessionRecord[]) => `${cut(groupName(r, sessions), GROUP_MAX)}/${r.title ?? r.branch ?? UNTITLED}`

export const GLYPH = { 'needs-you': sp('●', 'red'), running: sp('◐', 'yellow'), done: sp('✓', 'green'), ended: sp('○', 'dim') } as const

export const endedAt = (r: SessionRecord) => r.endedAt ?? r.lastActivityAt

// ---- Home ----

// What Home keeps while the pane has the keyboard: the order of each section, and who already waited when the
// keyboard arrived (a newer one is marked new).
export type Frozen = { needs: string[]; running: string[]; seenNeeds: string[] }
export type HomeModel = PaneModel & { loading: boolean; frozen: Frozen }

const inOrder = <T extends { sessionId: string }>(list: T[], order: string[] | undefined): T[] => {
  if (order === undefined) return list
  const at = (r: T) => order.indexOf(r.sessionId)
  const known = list.filter(r => at(r) >= 0).sort((a, b) => at(a) - at(b))
  return [...known, ...list.filter(r => at(r) < 0)]
}

// Oldest wait first (dir 1) or newest first (dir -1); a session whose wait is unknown comes last either way.
const bySince = (dir: 1 | -1) => (a: SessionRecord, b: SessionRecord) =>
  Number(a.engine.since === null) - Number(b.engine.since === null) || dir * ((a.engine.since ?? 0) - (b.engine.since ?? 0)) || dir * a.sessionId.localeCompare(b.sessionId)

const REASON_W = 13
const TIME_W = 5
const LABEL_MAX = 30
export const REASON = { permission: 'permission', question: 'question', waiting: 'waiting', unknown: 'state unknown' } as const

const sessionKey = (r: SessionRecord) => `session:${r.sessionId}`

// "● web-app/fix-login   permission   4m": the wait is dim, the reason and the dot red.
const needsRow = (r: SessionRecord, sessions: SessionRecord[], selfId: string, now: number, columns: number, isNew: boolean): Block => {
  const lw = clamp(columns - 2 - 1 - REASON_W - 1 - TIME_W, 10, LABEL_MAX)
  const label = r.sessionId === selfId ? THIS_SESSION : rowLabel(r, sessions)
  const waited = r.engine.since === null ? '' : duration(now - r.engine.since)
  const line: Spans = [GLYPH['needs-you'], sp(' '), sp(pad(cut(label, lw), lw)), sp(' '), sp(pad(REASON[r.reason ?? 'waiting'], REASON_W), 'red'), sp(' '), dim(waited), ...(isNew ? [sp(` ${NEW_MARK}`, 'cyan')] : [])]
  return { kind: 'row', key: sessionKey(r), to: { kind: 'session', id: r.sessionId }, lines: [line] }
}

// "◐ claude-tools/tracker   step 3/7 ▓▓▓▓░░░░░░ 43%": a session on a milestone shows its progress, else how long it has run.
const runningRow = (r: SessionRecord, sessions: SessionRecord[], now: number, columns: number): Block => {
  const m = r.milestone
  const done = m ? completeCount(m.features) : 0
  const total = m ? m.features.length : 0
  const goal = r.runs.goalSince !== null
  const lead = goal ? [sp('/goal', 'cyan'), sp(' ')] : m ? [dim('step ')] : []
  const progress = m && total > 0 ? `${done}/${total}` : ''
  const barWidth = 10
  const tail = m && total > 0 ? 1 + cells(progress) + 1 + barWidth + 1 + 4 : TIME_W
  const lw = clamp(columns - 2 - 1 - cells(lead.map(x => x.text).join('')) - tail, 8, LABEL_MAX)
  const waited = r.engine.since === null ? '' : duration(now - r.engine.since)
  const right: Spans = m && total > 0 ? [sp(progress), sp(' '), ...bar(done, total, barWidth), sp(' '), dim(`${percent(done, total)}%`)] : [dim(waited)]
  const line: Spans = [GLYPH.running, sp(' '), sp(pad(cut(rowLabel(r, sessions), lw), lw)), sp(' '), ...lead, ...right]
  return { kind: 'row', key: sessionKey(r), to: { kind: 'session', id: r.sessionId }, lines: [line] }
}

// The repos with a session, the most recent first, each with the state that matters most (F42).
export type RepoEntry = { path: string; label: string; needs: number; running: number }
export const repoEntries = (sessions: SessionRecord[]): RepoEntry[] => {
  const by = new Map<string, RepoEntry & { at: number }>()
  for (const r of sessions) {
    if (!r.repo) continue
    const e = by.get(r.repo.path) ?? { path: r.repo.path, label: repoLabel(r), needs: 0, running: 0, at: 0 }
    by.set(r.repo.path, { ...e, at: Math.max(e.at, r.lastActivityAt, r.endedAt ?? 0), needs: e.needs + Number(isLive(r) && r.state === 'needs-you'), running: e.running + Number(isLive(r) && r.state === 'running') })
  }
  return [...by.values()].sort((a, b) => b.at - a.at || a.path.localeCompare(b.path)).map(({ at: _at, ...e }) => e)
}

export const homeModel = (snap: Snapshot, selfId: string, now: number, local: Local, frozen: Frozen | null, columns: number): HomeModel => {
  const sessions = snap.sessions
  const live = sessions.filter(isLive)
  const of = (state: SessionRecord['state']) => live.filter(r => r.state === state)
  const alone = live.length === 1 && live[0]!.sessionId === selfId && live[0]!.state !== 'needs-you'
  const isStale = snap.at !== 0 && snap.failedReads >= 2
  const loading = snap.at === 0

  const needsList = inOrder(of('needs-you').sort(bySince(1)), frozen?.needs)
  const seen = frozen?.seenNeeds
  const runningAll = alone ? [] : inOrder(of('running').sort(bySince(1)), frozen?.running)
  const runningList = runningAll.slice(0, RUN_MAX)
  // Only sessions in a repo count: the folders no repo holds (background helpers) would drown the number.
  const doneToday = sessions.filter(r => r.repo !== null && ((isLive(r) && r.state === 'done') || (r.state === 'ended' && endedAt(r) >= local.midnight))).length
  const prs = prsOf(sessions, now)
  const lost = sessions.filter(r => r.source !== 'mod' && r.state !== 'ended').length

  const model = { frozen: { needs: needsList.map(r => r.sessionId), running: runningAll.map(r => r.sessionId), seenNeeds: seen ?? needsList.map(r => r.sessionId) } }
  const header: Pick<PaneModel, 'crumbs' | 'right'> = {
    crumbs: [{ text: 'Agent tracker', to: null, bold: true }],
    right: loading ? [] : join([[dim(`${live.length} live`)], needsList.length > 0 ? [sp(`${needsList.length} need you`, 'red')] : [dim('all clear')]]),
  }
  if (loading) return { ...model, ...header, loading, blocks: [{ kind: 'rule' }, { kind: 'lines', key: 'loading', lines: [[dim('Reading sessions…')]] }], footer: null, first: null }

  const blocks: Block[] = [{ kind: 'rule' }]
  if (isStale) blocks.push({ kind: 'lines', key: 'stale', wrap: true, lines: [[sp(staleTop(snap.okAt > 0 ? duration(Math.max(0, now - snap.okAt)) : null), 'yellow')]] })
  if (prs.partial) blocks.push({ kind: 'lines', key: 'partial', wrap: true, lines: [[dim(PRS_NOT_SHOWN)]] })
  const dimIf = (b: Block): Block => (isStale && b.kind === 'row' ? { ...b, lines: b.lines.map(l => l.map(x => ({ ...x, tone: 'dim' as const }))) } : b)

  blocks.push({ kind: 'lines', key: 'needs-head', lines: [heading(HEADINGS.needs, 'red')] })
  if (needsList.length > 0) blocks.push(...needsList.map(r => dimIf(needsRow(r, sessions, selfId, now, columns, seen !== undefined && !seen.includes(r.sessionId)))))
  else blocks.push({ kind: 'lines', key: 'needs-empty', lines: [[dim(alone ? ONLY_THIS : NOTHING_NEEDS)]] })

  if (runningList.length > 0) {
    blocks.push({ kind: 'rule' }, { kind: 'lines', key: 'running-head', lines: [heading(HEADINGS.running, 'yellow')] })
    blocks.push(...runningList.map(r => dimIf(runningRow(r, sessions, now, columns))))
    if (runningAll.length > RUN_MAX) blocks.push({ kind: 'lines', key: 'running-more', lines: [[dim(moreLine(runningAll.length - RUN_MAX))]] })
  }

  const summary: Spans = [
    ...(doneToday > 0 ? [sp('✓', 'green'), sp(` done today ${doneToday}`)] : []),
    ...(prs.prs ? [...(doneToday > 0 ? [sp('     ')] : []), dim('PRs '), sp(`${prs.prs.open} open`), ...(prs.prs.failing > 0 ? [DOT, sp(`${prs.prs.failing} red`, 'red')] : [])] : []),
  ]
  if (summary.length > 0) blocks.push({ kind: 'rule' }, { kind: 'lines', key: 'summary', lines: [summary] })

  const entries = repoEntries(sessions)
  if (entries.length === 0) blocks.push({ kind: 'lines', key: 'repos-none', lines: [[dim(NO_REPOS)]] })
  else {
    const shown = entries.slice(0, REPOS_MAX)
    const items: Item[] = shown.map(e => ({ key: `repos:${e.path}`, to: { kind: 'repo', path: e.path }, spans: [sp(e.label), ...(e.needs > 0 ? [sp(' ●', 'red')] : e.running > 0 ? [sp(' ◐', 'yellow')] : [])] }))
    if (entries.length > shown.length) items.push({ key: 'repos:more', spans: [dim(`+${entries.length - shown.length}`)] })
    blocks.push({ kind: 'inline', key: 'repos', head: [sp('REPOS', undefined, { bold: true }), sp('  ')], items, sep: DOT })
  }
  if (lost > 0) blocks.push({ kind: 'lines', key: 'without-tracker', lines: [[dim(withoutTracker(lost))]] })

  return { ...model, ...header, loading, blocks, footer: hint(updatedWords(duration(Math.max(0, now - snap.at)))), first: firstKey(blocks) }
}
