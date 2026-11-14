// The band as plain data: what the snapshot says (bandData), and how the compact row fits a width (compactLayout).
// Widths are terminal cells. spec/screens.md gives the measured sizes; the tests hold this to them.
import type { Pr, SessionRecord, Snapshot } from '../types'
import { duration, plural } from './format'
import { repoPrs } from './git'
import { completeCount, isComplete } from './milestone'
import type { Line } from './rank'
import { doneLines, isLive, needsLines, repoLabel, runningLines } from './rank'
import { DETACHED, LOADING, PRS_NOT_SHOWN, SHORT_REASON, THIS_SESSION, UNTITLED, staleWords } from './words'

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
  prs: { rows: PrRow[]; open: number; failing: number; mergeable: number } | null // null: gh gave nothing, so no PR segment (F54)
  partial: boolean // gh was asked and failed
  work: Work | null // this session's work
}

// Open PRs of every repo with a session in 7 days, each from its latest stored scan (F78). A repo whose gh failed
// adds nothing; with none left the PR segment is dropped.
const prsOf = (sessions: SessionRecord[], now: number): Pick<BandData, 'prs' | 'partial'> => {
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
    prs: ok ? { rows, open: rows.length, failing: rows.filter(x => x.pr.checks === 'failing').length, mergeable: rows.filter(x => x.pr.mergeable === 'mergeable').length } : null,
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

export const bandData = (snap: Snapshot, selfId: string, now: number): BandData => {
  const live = snap.sessions.filter(isLive)
  return {
    loading: snap.at === 0,
    stale: snap.at !== 0 && snap.failedReads >= 2 ? { ageMs: snap.okAt > 0 ? Math.max(0, now - snap.okAt) : null } : null,
    needs: needsLines(snap.sessions, selfId, now),
    running: runningLines(snap.sessions, selfId, now),
    done: doneLines(snap.sessions, selfId, now),
    live: live.length,
    ...prsOf(snap.sessions, now),
    work: workOf(snap.sessions.find(r => r.sessionId === selfId), now),
  }
}

export type Tone = 'warning' | 'dim' | 'error'
export type Chunk = { text: string; tone?: Tone }
export type Segment = { id: 'loading' | 'work' | 'needs' | 'run' | 'prs' | 'tail' | 'stale'; chunks: Chunk[] }

export const cells = (text: string) => [...text].length
const segmentCells = (s: Segment) => s.chunks.reduce((n, c) => n + cells(c.text), 0)

// A plain Button draws its label alone. The buttons sit 2 cells apart and 2 cells after the text. Compact has Pane and
// Details: 4 + 7 + 2 + 2 = 15 cells.
const GAP = 2
const buttonCells = (labels: readonly string[]) => labels.reduce((n, label) => n + cells(label), 0) + GAP * labels.length
export const BUTTONS_COMPACT = buttonCells(['Pane', 'Details'])
// Details has Copy, Pane and Compact: 4 + 4 + 7 + 6 = 21 cells.
export const BUTTONS_DETAILS = buttonCells(['Copy', 'Pane', 'Compact'])

// Each segment carries the spaces before it, so the row's width is the cells of its text and the buttons.
const rowWidth = (segments: Segment[], buttons: number) => segments.reduce((n, s) => n + segmentCells(s), 0) + buttons

// The owner's mockup (2026-11-14), work first: "agent-tracker-1 3/7 goal 42m · ● 2 need you  ◐3  PRs 1✗ 1↓  · fix-login waits 4m".
// The drop order, one step at a time: 1 the waiting session, 2 PRs, 3 the goal age, 4 the work shortened, 5 the work,
// 6 the running count. The need-you count and the buttons never drop. Below 40 columns: step 6 at once.
const LAST_STEP = 6
const SPACES = '  '

// A wait as it follows a name: " 6m", nothing when it is unknown.
const wait = (ms: number | null) => (ms === null ? '' : ` ${duration(ms)}`)

const workSegment = (w: Work, step: number): Segment => {
  const m = w.milestone
  const name = step < 4 ? (m ? `${m.slug} ${m.done}/${m.total}` : `${w.repo} · ${w.title ?? UNTITLED}`) : m ? `${m.done}/${m.total}` : w.repo
  return { id: 'work', chunks: [{ text: w.goalMs !== null && step < 3 ? `${name} goal ${duration(w.goalMs)}` : name }] }
}

const needsSegment = (d: BandData, afterWork: boolean): Segment => {
  const lead: Chunk[] = afterWork ? [{ text: ' · ' }] : []
  const n = d.needs.length
  return { id: 'needs', chunks: [...lead, n === 0 ? { text: '○ all clear', tone: 'dim' } : { text: `● ${n} ${n === 1 ? 'needs' : 'need'} you`, tone: 'warning' }] }
}

const prsSegment = (p: NonNullable<BandData['prs']>): Segment => {
  const parts = [p.failing > 0 ? `${p.failing}✗` : '', p.mergeable > 0 ? `${p.mergeable}↓` : ''].filter(Boolean)
  return { id: 'prs', chunks: [{ text: `${SPACES}PRs ${parts.length > 0 ? parts.join(' ') : p.open}` }] }
}

// The session waiting longest: "· fix-login waits 4m", or "this session" when it is this one.
const tailSegment = (l: Line): Segment => ({ id: 'tail', chunks: [{ text: `${SPACES}· ${l.self ? THIS_SESSION : l.title} waits${wait(l.ms)}` }] })

const build = (d: BandData, step: number, stale: string | null): Segment[] => {
  if (d.loading) return [{ id: 'loading', chunks: [{ text: LOADING, tone: 'dim' }] }]
  // A stale list gives its own words the place of the work.
  const work = d.work && stale === null && step < 5 ? workSegment(d.work, step) : null
  const segments: Segment[] = [...(work ? [work] : []), needsSegment(d, work !== null)]
  if (step < 6) segments.push({ id: 'run', chunks: [{ text: `${SPACES}◐${d.running.length}` }] })
  if (d.prs && step < 2) segments.push(prsSegment(d.prs))
  if (d.needs.length > 0 && step < 1) segments.push(tailSegment(d.needs[0]!))
  if (stale !== null) segments.push({ id: 'stale', chunks: [{ text: `${SPACES}${stale}` }] })
  // A stale list dims the counts it last read; its own words stay.
  return d.stale ? segments.map(s => (s.id === 'stale' ? s : { ...s, chunks: s.chunks.map(c => ({ ...c, tone: 'dim' as const })) })) : segments
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

// ---- The details view: two header lines, a rule, and the columns.

export type Column = { key: 'needs' | 'running' | 'prs'; label: string; count: string; line: string; tone?: Tone }
export type Details = {
  header: string[] // the first line sits beside the buttons; the second holds what runs and the other sessions
  note: string | null // Loading, Stale or Partial, in one line under the header (F87)
  rows: Column[][] // three columns in a row; below 60 columns two and one
  colWidth: number // the cells of a column, its 1 cell of space included
}

const JOIN = ' · '
// The columns of the mockup: 21 cells each, packed from the left, never stretched to the terminal.
export const COLUMN_CELLS = 21

// "/goal running 42m · 2 subagents · 1 background session · ● 2 need you elsewhere · 6 live": each part only when there is one.
const runsParts = (w: Work | null, d: BandData) =>
  [
    w === null || w.goalMs === null ? '' : `/goal running ${duration(w.goalMs)}`,
    w !== null && w.subagents > 0 ? plural(w.subagents, 'subagent', 'subagents') : '',
    w !== null && w.background > 0 ? plural(w.background, 'background session', 'background sessions') : '',
    d.needs.some(l => !l.self) ? `● ${d.needs.filter(l => !l.self).length} need you elsewhere` : '',
    d.live > 0 ? `${d.live} live` : '',
  ].filter(Boolean)

// The first line's cut ladder: 0 all, 1 no current feature, 2 no milestone name; without sdlc-run 1 no branch, 2 no title (F84).
const headerAt = (w: Work, level: number) => {
  const m = w.milestone
  const parts = [w.repo]
  if (m) {
    if (level < 2) parts.push(m.slug)
    const progress = `◐ ${m.done}/${m.total}`
    parts.push(level < 1 && w.feature !== null ? `${w.feature} ${progress}` : progress)
  } else {
    if (level < 2) parts.push(w.title ?? UNTITLED)
    const branch = w.branch ?? (w.hasRepo ? DETACHED : null)
    if (level < 1 && branch !== null) parts.push(branch)
  }
  return parts.join(JOIN)
}

const headerLines = (d: BandData, columns: number): string[] => {
  const w = d.work
  const parts = runsParts(w, d)
  // The second line gives up its last parts before it wraps.
  while (parts.length > 1 && cells(parts.join(JOIN)) > columns) parts.pop()
  const second = parts.length > 0 ? [parts.join(JOIN)] : []
  if (w === null) return ['', ...second]
  const room = columns - BUTTONS_DETAILS
  let line = headerAt(w, 2)
  for (let level = 0; level <= 2; level++) {
    if (cells(headerAt(w, level)) <= room) {
      line = headerAt(w, level)
      break
    }
  }
  return [line, ...second]
}

const column = (key: Column['key'], label: string, count: string, line: string, tone?: Tone): Column => ({ key, label, count, line, ...(tone ? { tone } : {}) })
const cut = (s: string, max: number) => (cells(s) > max ? `${[...s].slice(0, Math.max(1, max - 1)).join('')}…` : s)

// A name and what follows it: the name gives way to "…" first, so the wait or the progress stays whole.
const named = (name: string, tail: string, max: number) => `${cut(name, Math.max(1, max - cells(tail)))}${tail}`
// "fix-login · perm 4m" for the session waiting longest, "this session · perm 4m" when it is this one.
const needLine = (l: Line, max: number) => named(l.self ? THIS_SESSION : l.title, ` · ${SHORT_REASON[l.reason ?? 'waiting']}${wait(l.ms)}`, max)
// "tracker 3/7 · 43%" for the session running longest, else its name and how long it has run.
const runLine = (l: Line, max: number) => named(l.title, l.progress && l.progress.total > 0 ? ` ${l.progress.done}/${l.progress.total} · ${Math.round((100 * l.progress.done) / l.progress.total)}%` : wait(l.ms), max)

export const detailsLayout = (d: BandData, columns: number): Details => {
  const age = d.stale === null || d.stale.ageMs === null ? null : duration(d.stale.ageMs)
  const note = d.loading ? LOADING : d.stale ? staleWords(age, columns)[0]! : d.partial ? PRS_NOT_SHOWN : null
  const lines = columns >= 80 // below 80 the lines drop, except needs you
  const [need, run] = [d.needs[0], d.running[0]]
  const fold = columns < 60
  const colWidth = Math.min(COLUMN_CELLS, Math.floor(columns / (fold ? 2 : 3)))
  const prs = d.prs ? [column('prs', 'PRs', `${d.prs.open} open`, lines ? [d.prs.failing > 0 ? `${d.prs.failing} ✗` : '', d.prs.mergeable > 0 ? `${d.prs.mergeable} mergeable` : ''].filter(Boolean).join(JOIN) : '', 'dim')] : []
  const cols: Column[] = d.loading
    ? []
    : [
        column('needs', 'needs you', String(d.needs.length), need ? needLine(need, colWidth - 1) : ''),
        column('running', 'running', String(d.running.length), lines && run ? runLine(run, colWidth - 1) : '', 'dim'),
        ...prs,
      ].map(c => ({ ...c, line: cut(c.line, colWidth - 1), ...(d.stale ? { tone: 'dim' as const } : {}) })) // a stale list dims the last counts
  const rows = fold ? [cols.slice(0, 2), cols.slice(2)].filter(r => r.length > 0) : cols.length > 0 ? [cols] : []
  return { header: headerLines(d, columns), note, rows, colWidth }
}

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const fit = (s: string, max: number) => (s.length > max ? `${s.slice(0, Math.max(1, max - 1))}…` : s)
const FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
// The image cannot read the app's theme, so it follows the system's.
const STYLE = `.l,.s{fill:#87867f;font:12px ${FONT}}.v{fill:#1f1e1d;font:600 16px ${FONT}}.n{fill:#1f1e1d;font:12px ${FONT}}.d{stroke:#1f1e1d;stroke-opacity:.12}@media (prefers-color-scheme:dark){.v,.n{fill:#ecebe6}.d{stroke:#fff;stroke-opacity:.14}}`

// The columns as one image for the desktop: real dividers and exact columns (F37), 160 pixels each, packed from the left.
export const columnsSvg = (cols: Column[], colW = 160): string => {
  const height = 64
  const width = colW * Math.max(1, cols.length)
  let body = `<line class="d" x1="0" y1="0.5" x2="${width}" y2="0.5"/>`
  cols.forEach((c, i) => {
    const x = i * colW + (i === 0 ? 0 : 12)
    if (i > 0) body += `<line class="d" x1="${i * colW}" y1="14" x2="${i * colW}" y2="${height - 2}"/>`
    body += `<text class="l" x="${x}" y="24">${esc(c.label)}</text>`
    body += `<text class="v" x="${x}" y="44">${esc(fit(c.count, Math.floor((colW - 16) / 9)))}</text>`
    if (c.line) body += `<text class="${c.tone === 'dim' ? 's' : 'n'}" x="${x}" y="61">${esc(fit(c.line, Math.floor((colW - 16) / 6.2)))}</text>`
  })
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><style>${STYLE}</style>${body}</svg>`
}

// What the image says to a reader that cannot see it: every label, count and line.
export const columnsAlt = (cols: Column[]) => cols.map(c => `${c.label} ${c.count}${c.line ? `: ${c.line}` : ''}`).join(', ')
