// The band as plain data: what the snapshot says (bandData), and how the compact row fits a width (compactLayout).
// Widths are terminal cells. spec/screens.md gives the measured sizes; the tests hold this to them.
import type { Pr, SessionRecord, Snapshot } from '../types'
import { cells, cut, duration, plural } from './format'
import { DOT, cutSpans, dim, dimmed, join, sp, spanCells } from './paint'
import type { Span, Spans, Tone } from './paint'
import { repoPrs } from './git'
import type { NoteItem } from './notes'
import { unseenCount } from './notes'
import { completeCount, isComplete } from './milestone'
import type { Line } from './rank'
import { doneLines, isLive, needsLines, repoLabel, runningLines } from './rank'
import { BUTTON_LABELS, DETACHED, LOADING, PRS_NOT_SHOWN, SHORT_REASON, THIS_SESSION, UNTITLED, staleWords } from './words'

export type PrRow = { repo: string; pr: Pr }
export type Work = {
  milestone: { slug: string; done: number; total: number } | null
  repo: string
  hasRepo: boolean
  title: string | null
  branch: string | null
  feature: string | null // the feature being built, in an sdlc-run repo
  goalMs: number | null
  subagents: number
  background: number
}

export type BandData = {
  loading: boolean // the first read is pending (F53)
  stale: { ageMs: number | null } | null // the list failed twice in a row (F52); null age: no read ever worked
  needs: Line[] // oldest wait first
  running: Line[] // longest first
  done: Line[] // latest first
  live: number // sessions live in the list
  prs: { rows: PrRow[]; open: number; failing: number; behind: number } | null // null: gh gave nothing, so no PR segment (F54)
  partial: boolean // gh was asked and failed
  notes: { know: number; decided: number; topKnow: string | null; topDecided: string | null } // unseen counts, and the newest unseen item of each kind
  work: Work | null // this session's work
}

// Open PRs of every repo with a session in 7 days, each from its latest stored scan (F78). A repo whose gh failed
// adds nothing; with none left the PR segment is dropped.
export const prsOf = (sessions: SessionRecord[], now: number): Pick<BandData, 'prs' | 'partial'> => {
  const repos = new Map<string, string>()
  for (const r of sessions) if (r.repo) repos.set(r.repo.path, r.repo.name)
  const rows: PrRow[] = []
  let ok = false
  let asked = false
  for (const [path, name] of repos) {
    const p = repoPrs(sessions, path, now)
    if (p === null || !p.github) continue // not on GitHub: gh was never asked (R9)
    asked = true
    if (!p.ghOk) continue
    ok = true
    rows.push(...p.prs.map(pr => ({ repo: name, pr })))
  }
  return {
    prs: ok ? { rows, open: rows.length, failing: rows.filter(x => x.pr.checks === 'failing').length, behind: rows.filter(x => x.pr.behind === true).length } : null,
    partial: asked && !ok,
  }
}

const workOf = (r: SessionRecord | undefined, now: number): Work | null =>
  r === undefined
    ? null
    : {
        milestone: r.milestone ? { slug: r.milestone.slug, done: completeCount(r.milestone.features), total: r.milestone.features.length } : null,
        repo: repoLabel(r),
        hasRepo: r.repo !== null,
        title: r.title,
        branch: r.branch,
        feature: r.milestone?.features.find(f => !isComplete(f.state))?.name ?? null,
        // The goal's age shows only while the session runs or needs you (F11).
        goalMs: r.runs.goalSince === null || (r.state !== 'running' && r.state !== 'needs-you') ? null : Math.max(0, now - r.runs.goalSince),
        subagents: r.runs.subagents.length,
        background: r.runs.background.length,
      }

export const bandData = (snap: Snapshot, selfId: string, now: number, items: NoteItem[] = []): BandData => {
  const live = snap.sessions.filter(isLive)
  return {
    loading: snap.at === 0,
    stale: snap.at !== 0 && snap.failedReads >= 2 ? { ageMs: snap.okAt > 0 ? Math.max(0, now - snap.okAt) : null } : null,
    needs: needsLines(snap.sessions, selfId, now),
    running: runningLines(snap.sessions, selfId, now),
    done: doneLines(snap.sessions, selfId, now),
    live: live.length,
    ...prsOf(snap.sessions, now),
    notes: { know: unseenCount(items, 'know'), decided: unseenCount(items, 'decided'), topKnow: items.find(i => i.kind === 'know' && !i.seen)?.text ?? null, topDecided: items.find(i => i.kind === 'decided' && !i.seen)?.text ?? null },
    work: workOf(snap.sessions.find(r => r.sessionId === selfId), now),
  }
}

// A segment of the compact row. `id` says what it is; each segment carries the gap before it.
export type Chunk = Span
export type Segment = { id: 'label' | 'loading' | 'work' | 'needs' | 'run' | 'know' | 'decided' | 'prs' | 'tail' | 'stale'; chunks: Chunk[] }

const segmentCells = (s: Segment) => spanCells(s.chunks)

// A plain Button draws its label alone. The buttons sit 2 cells apart and 2 cells after the text. Compact has Pane, Board,
// Details and [–]: 4 + 5 + 7 + 3 + 2 * 4 = 27 cells.
const GAP = 2
const buttonCells = (labels: readonly string[]) => labels.reduce((n, label) => n + cells(label), 0) + GAP * labels.length
export const BUTTONS_COMPACT = buttonCells([BUTTON_LABELS.pane, BUTTON_LABELS.board, BUTTON_LABELS.details, BUTTON_LABELS.hide])
// Details has Copy, Pane, Board, Compact and [–]: 4 + 4 + 5 + 7 + 3 + 2 * 5 = 33 cells.
export const BUTTONS_DETAILS = buttonCells([BUTTON_LABELS.copy, BUTTON_LABELS.pane, BUTTON_LABELS.board, BUTTON_LABELS.compact, BUTTON_LABELS.hide])

// Each segment carries the spaces before it, so the row's width is the cells of its text and the buttons.
const rowWidth = (segments: Segment[], buttons: number) => segments.reduce((n, s) => n + segmentCells(s), 0) + buttons

// The owner's mockup (2026-11-14): "agent tracker M1 3/7 goal 42m · ● 2 need you  ◐3  !2  ◆2  PRs 1✗ 1↓  · fix-login waits 4m".
// The drop order, one step at a time: 1 the waiting session, 2 PRs, 3 the !N and ◆N counts, 4 the goal age, 5 the work
// shortened, 6 the work, 7 the label, 8 the running count. The need-you count and the buttons never drop. Below 40 columns: step 8 at once.
const LAST_STEP = 8
const SPACES = '  '
export const LABEL = 'agent tracker'

// A wait as it follows a name: " 6m", nothing when it is unknown.
const wait = (ms: number | null) => (ms === null ? '' : ` ${duration(ms)}`)

const labelSegment: Segment = { id: 'label', chunks: [sp(LABEL, 'label', { bold: true })] }

const workSegment = (w: Work, step: number): Segment => {
  const m = w.milestone
  const goal = w.goalMs !== null && step < 4 ? [sp(` goal ${duration(w.goalMs)}`, 'cyan')] : []
  const name = m ? [sp(step < 5 ? `${m.slug} ${m.done}/${m.total}` : `${m.done}/${m.total}`, 'yellow')] : [sp(step < 5 ? `${w.repo} · ${w.title ?? UNTITLED}` : w.repo)]
  return { id: 'work', chunks: [...name, ...goal] }
}

const needsSegment = (d: BandData): Segment => {
  const n = d.needs.length
  return { id: 'needs', chunks: [n === 0 ? sp('○ all clear', 'dim') : sp(`● ${n} ${n === 1 ? 'needs' : 'need'} you`, 'red')] }
}

const prsSegment = (p: NonNullable<BandData['prs']>): Segment => {
  const parts = [p.failing > 0 ? sp(`${p.failing}✗`, 'red') : null, p.behind > 0 ? sp(`${p.behind}↓`, 'yellow') : null].filter((x): x is Span => x !== null)
  return { id: 'prs', chunks: [dim('PRs '), ...(parts.length > 0 ? parts.flatMap((x, i) => (i === 0 ? [x] : [sp(' '), x])) : [sp(String(p.open))])] }
}

// The session waiting longest: "· fix-login waits 4m", or "this session" when it is this one; "waiting" alone when the start is unknown.
const tailSegment = (l: Line): Segment => ({ id: 'tail', chunks: [dim(`· ${l.self ? THIS_SESSION : l.title} ${l.ms === null ? 'waiting' : `waits${wait(l.ms)}`}`)] })

// The gap before a segment: " · " between the work and the need-you count, two spaces elsewhere, none at the start.
const lead = (s: Segment, prev: Segment | undefined): Chunk[] => (prev === undefined ? [] : s.id === 'needs' && prev.id === 'work' ? [DOT] : [sp(SPACES)])

const build = (d: BandData, step: number, stale: string | null): Segment[] => {
  const body: Segment[] = []
  if (d.loading) body.push({ id: 'loading', chunks: [dim(LOADING)] })
  else {
    // A stale list gives its own words the place of the work.
    const work = d.work && stale === null && step < 6 ? workSegment(d.work, step) : null
    if (work) body.push(work)
    body.push(needsSegment(d))
    if (step < 8) body.push({ id: 'run', chunks: [sp(`◐${d.running.length}`, 'yellow')] })
    if (step < 3 && d.notes.know > 0) body.push({ id: 'know', chunks: [sp(`!${d.notes.know}`, 'cyan')] })
    if (step < 3 && d.notes.decided > 0) body.push({ id: 'decided', chunks: [sp(`◆${d.notes.decided}`, 'magenta')] })
    if (d.prs && step < 2) body.push(prsSegment(d.prs))
    if (d.needs.length > 0 && step < 1) body.push(tailSegment(d.needs[0]!))
  }
  // A stale list dims the counts it last read; its own words stay.
  const read = d.stale ? body.map(s => ({ ...s, chunks: dimmed(s.chunks) })) : body
  const all = [...(step < 7 ? [labelSegment] : []), ...read, ...(stale !== null ? [{ id: 'stale' as const, chunks: [sp(stale, 'yellow')] }] : [])]
  return all.map((s, i) => ({ ...s, chunks: [...lead(s, all[i - 1]), ...s.chunks] }))
}

export type CompactLayout = { segments: Segment[]; width: number }

// The longest form that fits `columns` (bodyColumns). A stale line never drops: the other parts give way first (F28, F52).
export const compactLayout = (d: BandData, columns: number): CompactLayout => {
  const variants = d.stale ? staleWords(d.stale.ageMs === null ? null : duration(d.stale.ageMs), columns) : [null]
  const first = columns < 40 ? LAST_STEP : 0
  for (const stale of variants) {
    for (let step = first; step <= LAST_STEP; step++) {
      const segments = build(d, step, stale)
      if (rowWidth(segments, BUTTONS_COMPACT) <= columns) return { segments, width: rowWidth(segments, BUTTONS_COMPACT) }
    }
  }
  const segments = build(d, LAST_STEP, variants[variants.length - 1]!)
  return { segments, width: rowWidth(segments, BUTTONS_COMPACT) }
}

// ---- The details view: two header lines, a rule, and the five columns.

export type Column = { key: 'needs' | 'running' | 'know' | 'decided' | 'prs'; label: string; count: string; line: string; lineSpans: Spans; tone?: 'dim'; countTone?: Tone }
export type Details = {
  header: Spans[] // the first line sits beside the buttons; the second holds what runs and the other sessions
  note: string | null // Loading, Stale or Partial, in one line under the header (F87)
  rows: Column[][] // up to five columns in a row; fewer when the width is short
  colWidth: number // the cells of a column, its 1 cell of space included
}

const JOIN = ' · '
// The columns of the mockup: 21 cells each, packed from the left, never stretched to the terminal.
export const COLUMN_CELLS = 21
const GUTTER = 2 // a column's text leaves 2 cells before the next column

// "/goal running 42m · 2 subagents · 1 background session · ● 2 need you elsewhere · 6 live": each part only when there is one.
const runsParts = (w: Work | null, d: BandData): Spans[] => {
  const elsewhere = d.needs.filter(l => !l.self).length
  return [
    w === null || w.goalMs === null ? [] : [sp(`/goal running ${duration(w.goalMs)}`, 'cyan')],
    w !== null && w.subagents > 0 ? [dim(plural(w.subagents, 'subagent', 'subagents'))] : [],
    w !== null && w.background > 0 ? [dim(plural(w.background, 'background session', 'background sessions'))] : [],
    elsewhere > 0 ? [sp(`● ${elsewhere} need you`, 'red'), dim(' elsewhere')] : [],
    d.live > 0 ? [dim(`${d.live} live`)] : [],
  ].filter(p => p.length > 0)
}

// The first line's cut ladder: 0 all, 1 no current feature, 2 no milestone name; without sdlc-run 1 no branch, 2 no title (F84).
// "calvins-claude-tools · agent tracker · M1 collector ◐ 3/7": the repo in bold, the label in its colour, the progress in yellow.
const headerAt = (w: Work, level: number): Spans => {
  const m = w.milestone
  const parts: Spans[] = [[sp(w.repo, undefined, { bold: true })], [sp(LABEL, 'label', { bold: true })]]
  if (m) {
    const progress = sp(`◐ ${m.done}/${m.total}`, 'yellow')
    parts.push([...(level < 2 ? [sp(`${m.slug} `)] : []), ...(level < 1 && w.feature !== null ? [sp(`${w.feature} `)] : []), progress])
  } else {
    if (level < 2) parts.push([sp(w.title ?? UNTITLED)])
    const branch = w.branch ?? (w.hasRepo ? DETACHED : null)
    if (level < 1 && branch !== null) parts.push([sp(branch)])
  }
  return join(parts)
}

const headerLines = (d: BandData, columns: number): Spans[] => {
  const w = d.work
  const parts = runsParts(w, d)
  // The second line gives up its last parts before it wraps.
  while (parts.length > 1 && spanCells(join(parts)) > columns) parts.pop()
  const second = parts.length > 0 ? [join(parts)] : []
  if (w === null) return [[sp(LABEL, 'label', { bold: true })], ...second]
  const room = columns - BUTTONS_DETAILS
  let line = headerAt(w, 2)
  for (let level = 0; level <= 2; level++) {
    if (spanCells(headerAt(w, level)) <= room) {
      line = headerAt(w, level)
      break
    }
  }
  return [line, ...second]
}

const column = (key: Column['key'], label: string, count: string, line: string, lineSpans: Spans, o: { tone?: 'dim'; countTone?: Tone } = {}): Column => ({ key, label, count, line, lineSpans, ...o })
// A name and what follows it: the name gives way to "…" first, so the wait or the progress stays whole.
const named = (name: string, tail: string, max: number) => `${cut(name, Math.max(1, max - cells(tail)))}${tail}`
// "fix-login · perm 4m" for the session waiting longest, "this session · perm 4m" when it is this one.
const needLine = (l: Line, max: number) => named(l.self ? THIS_SESSION : l.title, ` · ${SHORT_REASON[l.reason ?? 'waiting']}${wait(l.ms)}`, max)
// "tracker 3/7 · 43%" for the session running longest, else its name and how long it has run.
const runLine = (l: Line, max: number) => named(l.title, l.progress && l.progress.total > 0 ? ` ${l.progress.done}/${l.progress.total} · ${Math.round((100 * l.progress.done) / l.progress.total)}%` : wait(l.ms), max)

// The PR column's line: "1 ✗ · 1 behind", the failing count in red, the behind count in yellow.
const prLine = (p: NonNullable<BandData['prs']>, max: number): { line: string; spans: Spans } => {
  const failing = p.failing > 0 ? `${p.failing} ✗` : ''
  const behind = p.behind > 0 ? `${p.behind} behind` : ''
  const line = cut([failing, behind].filter(Boolean).join(JOIN), max)
  const spans = [failing === '' ? [] : [sp(failing, 'red')], behind === '' ? [] : [sp(behind, 'yellow')]].filter(x => x.length > 0)
  return { line, spans: cutSpans(join(spans), max) }
}

// How many columns share a row: as many 21-cell ones as fit, and the rows kept even (five at 100 columns are 3 and 2).
export const perRow = (count: number, columns: number) => {
  const fit = Math.max(1, Math.min(count, Math.floor(columns / COLUMN_CELLS)))
  return Math.ceil(count / Math.ceil(count / fit))
}

export const detailsLayout = (d: BandData, columns: number): Details => {
  const age = d.stale === null || d.stale.ageMs === null ? null : duration(d.stale.ageMs)
  const note = d.loading ? LOADING : d.stale ? staleWords(age, columns)[0]! : d.partial ? PRS_NOT_SHOWN : null
  const lines = columns >= 80 // below 80 the lines drop, except needs you
  const [need, run] = [d.needs[0], d.running[0]]
  const per = perRow(5, columns)
  const colWidth = Math.min(COLUMN_CELLS, Math.floor(columns / per))
  const max = colWidth - GUTTER
  const text = (line: string, tone?: Tone) => ({ line: cut(line, max), lineSpans: line === '' ? [] : [sp(cut(line, max), tone)] })
  const pr = d.prs && lines ? prLine(d.prs, max) : { line: '', spans: [] as Spans }
  const news = (n: number) => `${n} new`
  const cols: Column[] = d.loading
    ? []
    : [
        { ...column('needs', 'needs you', String(d.needs.length), '', [], { countTone: d.needs.length > 0 ? 'red' : undefined }), ...text(need ? needLine(need, max) : '', 'dim') },
        { ...column('running', 'running', String(d.running.length), '', [], { tone: 'dim' }), ...text(lines && run ? runLine(run, max) : '', 'dim') },
        { ...column('know', 'you should know', news(d.notes.know), '', [], { countTone: d.notes.know > 0 ? 'cyan' : undefined }), ...text(lines ? (d.notes.topKnow ?? '') : '', 'dim') },
        { ...column('decided', 'decided without you', news(d.notes.decided), '', [], { countTone: d.notes.decided > 0 ? 'magenta' : undefined }), ...text(lines ? (d.notes.topDecided ?? '') : '', 'dim') },
        ...(d.prs ? [column('prs', 'PRs', `${d.prs.open} open`, pr.line, pr.spans, { tone: 'dim' })] : []),
      ].map(c => (d.stale ? { ...c, tone: 'dim' as const, lineSpans: dimmed(c.lineSpans), countTone: undefined } : c)) // a stale list dims the last counts
  const n = cols.length === 0 ? 0 : perRow(cols.length, columns)
  const rows = n === 0 ? [] : Array.from({ length: Math.ceil(cols.length / n) }, (_, i) => cols.slice(i * n, (i + 1) * n))
  return { header: headerLines(d, columns), note, rows, colWidth }
}

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const fit = (s: string, max: number) => (s.length > max ? `${s.slice(0, Math.max(1, max - 1))}…` : s)
const FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
// The image cannot read the app's theme, so it follows the system's.
const STYLE = `.l,.s{fill:#87867f;font:12px ${FONT}}.v{fill:#1f1e1d;font:600 16px ${FONT}}.r{fill:#d1242f}.c{fill:#0969da}.m{fill:#8250df}.n{fill:#1f1e1d;font:12px ${FONT}}.d{stroke:#1f1e1d;stroke-opacity:.12}@media (prefers-color-scheme:dark){.v,.n{fill:#ecebe6}.d{stroke:#fff;stroke-opacity:.14}}`

// The columns as one image for the desktop: real dividers and exact columns (F37), 160 pixels each, packed from the left.
export const columnsSvg = (cols: Column[], colW = 160): string => {
  const height = 64
  const width = colW * Math.max(1, cols.length)
  let body = `<line class="d" x1="0" y1="0.5" x2="${width}" y2="0.5"/>`
  cols.forEach((c, i) => {
    const x = i * colW + (i === 0 ? 0 : 12)
    if (i > 0) body += `<line class="d" x1="${i * colW}" y1="14" x2="${i * colW}" y2="${height - 2}"/>`
    body += `<text class="l" x="${x}" y="24">${esc(c.label)}</text>`
    body += `<text class="v${c.countTone === 'red' ? ' r' : c.countTone === 'cyan' ? ' c' : c.countTone === 'magenta' ? ' m' : ''}" x="${x}" y="44">${esc(fit(c.count, Math.floor((colW - 16) / 9)))}</text>`
    if (c.line) body += `<text class="${c.tone === 'dim' ? 's' : 'n'}" x="${x}" y="61">${esc(fit(c.line, Math.floor((colW - 16) / 6.2)))}</text>`
  })
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><style>${STYLE}</style>${body}</svg>`
}

// What the image says to a reader that cannot see it: every label, count and line.
export const columnsAlt = (cols: Column[]) => cols.map(c => `${c.label} ${c.count}${c.line ? `: ${c.line}` : ''}`).join(', ')
