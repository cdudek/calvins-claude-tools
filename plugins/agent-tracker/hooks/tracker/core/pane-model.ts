// The pane as plain data, as the owner's mockups draw it (2026-11-14): every page is a PaneModel, a header, then blocks of
// coloured lines, rows that are Buttons and inline lists. Time and the local day are parameters: nothing here reads a clock.
// Widths are terminal cells.
import type { SessionRecord, Snapshot } from '../types'
import { cut, duration, pad } from './format'
import { prsOf } from './band-model'
import { isLive, isNumbered, repoLabel, sessionLabel } from './rank'
import { dim, DOT, join, sp } from './paint'
import type { Span, Spans } from './paint'
import { HEADINGS, NOTHING_NEEDS, ONLY_THIS, NO_REPOS, NO_TASKS, NEW_MARK, PRS_NOT_SHOWN, THIS_SESSION, KEY_HINTS, staleTop, updatedWords, withoutTracker } from './words'
import type { NoteItem } from './notes'
import { isNews } from './notes'
import type { TaskItem } from './tasks'
import { TASK_LABEL, taskCounts } from './tasks'

export const RUN_MAX = 8 // Running rows on Home before "and N more"
export const REPOS_MAX = 8

export type Page =
  | { kind: 'home' }
  | { kind: 'session'; id: string }
  | { kind: 'repo'; path: string }
  | { kind: 'milestone'; repo: string; change: string }
  | { kind: 'feature'; repo: string; change: string; n: number }
  | { kind: 'note'; key: string }
  | { kind: 'missing'; what: 'session' | 'repo'; text: string }

// The day and the clock face are the I/O layer's: core never reads a time zone. `day` is the weekday of an older ask.
export type Local = { midnight: number; clock: (ms: number) => string; day: (ms: number) => string }

// A Button that does something other than open a page: mark notes seen, copy the reply to overrule one, copy a resume command,
// keep or close a task (`keys` are the task keys).
export type ActionItem = { key: string; label: string; action: 'seen' | 'overrule' | 'resume' | 'keep' | 'close'; keys?: string[] }

// One item of an inline list: a Button when it has `to`, a Link when it has `href`, plain text otherwise.
export type Item = { key: string; spans: Spans; to?: Page; href?: string; joined?: boolean } // joined: no separator before it
export type Block =
  | { kind: 'lines'; key: string; lines: Spans[]; wrap?: boolean }
  | { kind: 'rule' }
  | { kind: 'row'; key: string; to: Page; lines: Spans[] }
  | { kind: 'inline'; key: string; head: Spans; items: Item[]; sep: Span | null }
  | { kind: 'actions'; key: string; items: ActionItem[] }

// The breadcrumb: every crumb with a page is a Button; the last is the page itself.
export type Crumb = { text: string; to: Page | null; bold?: boolean }
export type PaneModel = { crumbs: Crumb[]; right: Spans; blocks: Block[]; footer: Spans | null; first: string | null }

export const rowsOf = (blocks: Block[]) => blocks.flatMap(b => (b.kind === 'row' || b.kind === 'actions' || b.kind === 'inline' ? [b] : []))
// The key a page's focus ring starts on: its first row, else the first item of its first inline list.
export const firstKey = (blocks: Block[]): string | null => {
  for (const b of blocks) {
    if (b.kind === 'row') return b.key
    if (b.kind === 'actions') return b.items[0]?.key ?? null
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
// "13:40" for today, "Tue" before.
export const when = (at: number, local: Local) => (at >= local.midnight ? local.clock(at) : local.day(at))
// A note's time: the clock for a turn's or a file's, the day alone ("today", "Tue") for a revision, which has none.
export const noteWhen = (i: { at: number; dayOnly: boolean }, local: Local) => (i.dayOnly ? (i.at >= local.midnight ? 'today' : local.day(i.at)) : when(i.at, local))
export const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))

// ---- names ----

const folder = (path: string) => path.replace(/\/+$/, '').split('/').pop() || path

export const GLYPH = { 'needs-you': sp('●', 'red'), running: sp('◐', 'yellow'), done: sp('✓', 'green'), ended: sp('○', 'dim') } as const

export const endedAt = (r: SessionRecord) => r.endedAt ?? r.lastActivityAt

// ---- Home ----

// What Home keeps while the pane has the keyboard: the order of Needs you, and who already waited when the keyboard
// arrived (a newer one is marked new).
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
const needsRow = (r: SessionRecord, selfId: string, now: number, columns: number, isNew: boolean): Block => {
  const lw = clamp(columns - 2 - 1 - REASON_W - 1 - TIME_W, 10, LABEL_MAX)
  const label = r.sessionId === selfId ? THIS_SESSION : sessionLabel(r)
  const waited = r.engine.since === null ? '' : duration(now - r.engine.since)
  const line: Spans = [GLYPH['needs-you'], sp(' '), sp(pad(cut(label, lw), lw)), sp(' '), sp(pad(REASON[r.reason ?? 'waiting'], REASON_W), 'red'), sp(' '), dim(waited), ...(isNew ? [sp(` ${NEW_MARK}`, 'cyan')] : [])]
  return { kind: 'row', key: sessionKey(r), to: { kind: 'session', id: r.sessionId }, lines: [line] }
}

// The repos with a session, the most recent first, each with the state that matters most (F42).
export type RepoEntry = { path: string; label: string; needs: number; running: number }
export const repoEntries = (sessions: SessionRecord[]): RepoEntry[] => {
  const by = new Map<string, RepoEntry & { at: number }>()
  for (const r of sessions) {
    if (!r.repo || isNumbered(r)) continue
    const e = by.get(r.repo.path) ?? { path: r.repo.path, label: repoLabel(r), needs: 0, running: 0, at: 0 }
    by.set(r.repo.path, { ...e, at: Math.max(e.at, r.lastActivityAt, r.endedAt ?? 0), needs: e.needs + Number(isLive(r) && r.state === 'needs-you'), running: e.running + Number(isLive(r) && r.state === 'running') })
  }
  return [...by.values()].sort((a, b) => b.at - a.at || a.path.localeCompare(b.path)).map(({ at: _at, ...e }) => e)
}

export const TASKS_SHOWN = 8 // task rows on Home before "and N more": the list leads the page and must leave the rest on the first screen

const TASK_STYLE = { 'needs-you': { glyph: '●', tone: 'red' }, forgotten: { glyph: '○', tone: 'red' }, superseded: { glyph: '?', tone: 'magenta' }, 'in-progress': { glyph: '◐', tone: 'yellow' } } as const

// "● Fix the login redirect", then "   web-app  asked 13:40  You: waiting for your answer for 4m". A superseded task adds Keep and Close.
const taskBlocks = (t: TaskItem, local: Local, columns: number): Block[] => {
  const st = TASK_STYLE[t.status]
  const detail =
    t.status === 'superseded'
      ? t.later === null ? 'a later ask may have replaced it' : `a later ask at ${when(t.later.at, local)}, “${t.later.text}”, may have replaced it`
      : t.status === 'in-progress' && t.progress !== null ? `${t.progress.slug}, ${t.progress.done} of ${t.progress.total} features` : t.detail
  const words = `${TASK_LABEL[t.status]}${detail === '' ? '' : `${t.status === 'superseded' ? ' ' : ': '}${detail}`}`
  const row: Block = {
    kind: 'row',
    key: `task:${t.key}`,
    to: { kind: 'session', id: t.sessionId },
    lines: [[sp(st.glyph, st.tone), sp(' '), sp(cut(t.text, columns - 4))], [sp('   '), sp(t.repo, undefined, { bold: true }), sp('  '), dim(`asked ${when(t.at, local)}`), sp('  '), sp(words, st.tone)]],
  }
  return t.status === 'superseded' ? [row, { kind: 'actions', key: `task-act:${t.key}`, items: [{ key: `keep:${t.key}`, label: 'Keep', action: 'keep', keys: [t.key] }, { key: `close:${t.key}`, label: 'Close', action: 'close', keys: [t.key] }] }] : [row]
}

export const NOTES_UNSEEN_SHOWN = 4 // unseen items of one kind on Home before "and N more"
export const NOTES_SEEN_SHOWN = 2 // seen items of one kind on Home, one line each

const NOTE_STYLE = { know: { head: HEADINGS.know, tone: 'cyan', glyph: '!' }, decided: { head: HEADINGS.decided, tone: 'magenta', glyph: '◆' } } as const

// One section of Home: "YOU SHOULD KNOW  2 new", an unseen item as two lines (label and time, then the text), a seen one as one dim line.
const noteSection = (kind: 'know' | 'decided', items: NoteItem[], local: Local, columns: number): Block[] => {
  const mine = items.filter(i => i.kind === kind)
  if (mine.length === 0) return []
  const st = NOTE_STYLE[kind]
  const unseen = mine.filter(isNews)
  const seen = mine.filter(i => !isNews(i)).slice(0, NOTES_SEEN_SHOWN) // seen notes, and a change folder's records by their source
  const lw = clamp(columns - 2 - 2 - TIME_W - 1, 10, LABEL_MAX)
  const row = (i: NoteItem): Block =>
    !isNews(i)
      ? { kind: 'row', key: `note:${i.key}`, to: { kind: 'note', key: i.key }, lines: [[dim(`· ${pad(cut(i.label, lw), lw)} ${noteWhen(i, local)}  ${i.seen ? 'seen' : (i.ref ?? 'file')}`)]] }
      : { kind: 'row', key: `note:${i.key}`, to: { kind: 'note', key: i.key }, lines: [[sp(st.glyph, st.tone), sp(' '), sp(pad(cut(i.label, lw), lw)), sp(' '), dim(noteWhen(i, local))], [sp('   '), sp(cut(i.text, columns - 4))]] }
  const more = unseen.length - NOTES_UNSEEN_SHOWN
  return [
    { kind: 'lines', key: `${kind}-head`, lines: [[sp(st.head, st.tone, { bold: true }), ...(unseen.length > 0 ? [sp('  '), sp(`${unseen.length} new`, st.tone)] : [])]] },
    ...unseen.slice(0, NOTES_UNSEEN_SHOWN).map(row),
    ...(more > 0 ? [{ kind: 'lines', key: `${kind}-more`, lines: [[dim(`and ${more} more, not seen`)]] } as Block] : []),
    ...seen.map(row),
  ]
}

export const homeModel = (snap: Snapshot, selfId: string, now: number, local: Local, frozen: Frozen | null, columns: number, items: NoteItem[] = [], tasks: TaskItem[] = []): HomeModel => {
  const sessions = snap.sessions
  const live = sessions.filter(isLive)
  const of = (state: SessionRecord['state']) => live.filter(r => r.state === state)
  const isStale = snap.at !== 0 && snap.failedReads >= 2
  const loading = snap.at === 0

  const needsList = inOrder(of('needs-you').sort(bySince(1)), frozen?.needs)
  const seen = frozen?.seenNeeds
  const running = of('running').length
  const prs = prsOf(sessions, now)
  // Only the sessions that run beside this tracker's own count: this session alone is no news.
  const lost = sessions.filter(r => r.source !== 'mod' && r.state !== 'ended').length

  const model = { frozen: { needs: needsList.map(r => r.sessionId), running: [], seenNeeds: seen ?? needsList.map(r => r.sessionId) } }
  const header: Pick<PaneModel, 'crumbs' | 'right'> = {
    crumbs: [{ text: 'Agent tracker', to: null, bold: true }],
    right: loading ? [] : join([[dim(`${live.length} live`)], needsList.length > 0 ? [sp(`${needsList.length} need you`, 'red')] : [dim('all clear')]]),
  }
  if (loading) return { ...model, ...header, loading, blocks: [{ kind: 'rule' }, { kind: 'lines', key: 'loading', lines: [[dim('Reading sessions…')]] }], footer: null, first: null }

  const blocks: Block[] = [{ kind: 'rule' }]
  if (isStale) blocks.push({ kind: 'lines', key: 'stale', wrap: true, lines: [[sp(staleTop(snap.okAt > 0 ? duration(Math.max(0, now - snap.okAt)) : null), 'yellow')]] })
  if (prs.partial) blocks.push({ kind: 'lines', key: 'partial', wrap: true, lines: [[dim(PRS_NOT_SHOWN)]] })
  const dimIf = (b: Block): Block => (isStale && b.kind === 'row' ? { ...b, lines: b.lines.map(l => l.map(x => ({ ...x, tone: 'dim' as const }))) } : b)

  // The owner's open tasks lead the page: the same list, order and colours as the Board.
  const counts = taskCounts(tasks)
  blocks.push({ kind: 'lines', key: 'tasks-head', lines: [heading(HEADINGS.tasks, counts.alarm ? 'red' : tasks.length > 0 ? 'yellow' : undefined, [sp('  '), sp(String(tasks.length), counts.alarm ? 'red' : tasks.length > 0 ? 'yellow' : 'dim')])] })
  if (tasks.length === 0) blocks.push({ kind: 'lines', key: 'tasks-empty', lines: [[dim(NO_TASKS)]] })
  blocks.push(...tasks.slice(0, TASKS_SHOWN).flatMap(t => taskBlocks(t, local, columns)))
  if (tasks.length > TASKS_SHOWN) blocks.push({ kind: 'lines', key: 'tasks-more', lines: [[dim(`and ${tasks.length - TASKS_SHOWN} more, all on the Board (/tracker web)`)]] })
  blocks.push({ kind: 'rule' })

  blocks.push({ kind: 'lines', key: 'needs-head', lines: [heading(HEADINGS.needs, 'red')] })
  if (needsList.length > 0) blocks.push(...needsList.map(r => dimIf(needsRow(r, selfId, now, columns, seen !== undefined && !seen.includes(r.sessionId)))))
  else blocks.push({ kind: 'lines', key: 'needs-empty', lines: [[dim(live.length === 1 && live[0]!.sessionId === selfId ? ONLY_THIS : NOTHING_NEEDS)]] })

  const know = noteSection('know', items, local, columns)
  const decided = noteSection('decided', items, local, columns)
  if (know.length > 0) blocks.push({ kind: 'rule' }, ...know)
  if (decided.length > 0) blocks.push(...(know.length > 0 ? [] : [{ kind: 'rule' } as Block]), ...decided)
  const unseen = items.filter(i => !i.seen).map(i => i.key)
  if (unseen.length > 0) blocks.push({ kind: 'actions', key: 'notes-actions', items: [{ key: 'allseen', label: 'Mark all seen', action: 'seen', keys: unseen }] })

  // "RUNNING  ◐ 2 sessions   PRs 4 · 1 behind · 1 red"
  const behind = prs.prs?.behind ?? 0
  const prParts: Spans = prs.prs
    ? [dim('PRs '), sp(String(prs.prs.open)), ...(behind > 0 ? [DOT, sp(`${behind} behind`, 'yellow')] : []), ...(prs.prs.failing > 0 ? [DOT, sp(`${prs.prs.failing} red`, 'red')] : [])]
    : []
  if (running > 0 || prParts.length > 0) {
    blocks.push({ kind: 'rule' }, { kind: 'lines', key: 'running', lines: [[sp(HEADINGS.running, 'yellow', { bold: true }), ...(running > 0 ? [sp('  '), sp(`◐ ${running} ${running === 1 ? 'session' : 'sessions'}`, 'yellow')] : []), ...(prParts.length > 0 ? [sp('   '), ...prParts] : [])]] })
  }

  const entries = repoEntries(sessions)
  if (entries.length === 0) blocks.push({ kind: 'lines', key: 'repos-none', lines: [[dim(NO_REPOS)]] })
  else {
    const shown = entries.slice(0, REPOS_MAX)
    const others = sessions.filter(r => isLive(r) && isNumbered(r)).length
    const items: Item[] = shown.map(e => ({ key: `repos:${e.path}`, to: { kind: 'repo', path: e.path }, spans: [sp(e.label), ...(e.needs > 0 ? [sp(' ●', 'red')] : e.running > 0 ? [sp(' ◐', 'yellow')] : [])] }))
    if (entries.length > shown.length) items.push({ key: 'repos:more', spans: [dim(`+${entries.length - shown.length}`)] })
    if (others > 0) items.push({ key: 'repos:other', spans: [dim(`other ${others}`)] })
    blocks.push({ kind: 'inline', key: 'repos', head: [sp('REPOS', undefined, { bold: true }), sp('  ')], items, sep: DOT })
  }
  // The note about sessions without the tracker goes last, one dim line.
  if (lost > 0) blocks.push({ kind: 'lines', key: 'without-tracker', lines: [[dim(withoutTracker(lost))]] })

  return { ...model, ...header, loading, blocks, footer: hint(updatedWords(duration(Math.max(0, now - snap.at)))), first: firstKey(blocks) }
}
