// The band as plain data: what the snapshot says (bandData), and how the compact row fits a width (compactLayout).
// Widths are terminal cells. spec/screens.md gives the measured sizes; the tests hold this to them.
import type { Pr, SessionRecord, Snapshot } from '../types'
import { duration, plural } from './format'
import { repoPrs } from './git'
import { completeCount } from './milestone'
import type { Line } from './rank'
import { doneLines, isLive, needsLines, repoLabel, runningLines } from './rank'
import { ALONE, DETACHED, LOADING, PRS_NOT_SHOWN, SEP, THIS_SESSION, UNTITLED, staleWords } from './words'

export type PrRow = { repo: string; pr: Pr }
export type Work = {
  milestone: { slug: string; done: number; total: number } | null
  repo: string
  hasRepo: boolean
  title: string | null
  branch: string | null
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
  alone: boolean // this is the only live session (F32)
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
    if (p === null) continue
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
    alone: live.length === 1 && live[0]!.sessionId === selfId,
    ...prsOf(snap.sessions, now),
    work: workOf(snap.sessions.find(r => r.sessionId === selfId), now),
  }
}

export type Tone = 'warning' | 'dim' | 'error'
export type Chunk = { text: string; tone?: Tone }
export type Segment = { id: 'loading' | 'needs' | 'run' | 'alone' | 'prs' | 'work' | 'stale'; chunks: Chunk[] }

export const cells = (text: string) => [...text].length
const segmentCells = (s: Segment) => s.chunks.reduce((n, c) => n + cells(c.text), 0)

// A plain Button with a hotkey draws "p: Pane": its label and three cells. Compact has Pane and Details (17 cells).
const buttonCells = (labels: readonly string[]) => labels.reduce((n, label) => n + cells(label) + 3, 0)
export const BUTTONS_COMPACT = buttonCells(['Pane', 'Details'])
// Details has Copy, Pane and Compact: 24 cells. The spec counts 21 (questions.md Q17).
export const BUTTONS_DETAILS = buttonCells(['Copy', 'Pane', 'Compact'])

const rowWidth = (segments: Segment[], buttons: number) => segments.reduce((n, s) => n + segmentCells(s), 0) + cells(SEP) * Math.max(0, segments.length - 1) + buttons

// The drop order, one step at a time: 1 goal age, 2 Work, 3 the words "running" and "done", 4 PRs, 5 the waiting
// session's title (the spec's five), then 6 the running and done counts and 7 the waiting session itself, so the
// line fits below 54 columns (questions.md Q16). Below 40 columns: step 7 at once.
const LAST_STEP = 7

const needsSegment = (d: BandData, step: number): Segment => {
  const n = d.needs.length
  if (n === 0) return { id: 'needs', chunks: [{ text: '0 need you', tone: 'dim' }] }
  const chunks: Chunk[] = [{ text: `● ${n} ${n === 1 ? 'needs' : 'need'} you`, tone: 'warning' }]
  if (step < 7) {
    const me = d.needs.find(l => l.self)
    if (me) {
      chunks.push({ text: ` · ${THIS_SESSION} ${duration(me.ms)}` })
      const other = d.needs.find(l => !l.self)
      if (other) chunks.push({ text: ` · ${other.repo} ${duration(other.ms)}` })
    } else {
      const first = d.needs[0]!
      chunks.push({ text: step < 5 ? ` · ${first.repo}: ${first.title} ${duration(first.ms)}` : ` · ${first.repo} ${duration(first.ms)}` })
    }
  }
  return { id: 'needs', chunks }
}

const workSegment = (w: Work, step: number): Segment => {
  const chunks: Chunk[] = [{ text: w.milestone ? `${w.milestone.slug} ${w.milestone.done}/${w.milestone.total}` : `${w.repo} · ${w.title ?? UNTITLED}` }]
  if (w.goalMs !== null && step < 1) chunks.push({ text: ` · goal ${duration(w.goalMs)}` })
  return { id: 'work', chunks }
}

const build = (d: BandData, step: number, stale: string | null): Segment[] => {
  if (d.loading) return [{ id: 'loading', chunks: [{ text: LOADING, tone: 'dim' }] }]
  const segments: Segment[] = [needsSegment(d, step)]
  if (d.alone) {
    if (step < 4) segments.push({ id: 'alone', chunks: [{ text: ALONE, tone: 'dim' }] })
  } else if (step < 6) {
    const words = step < 3
    segments.push({
      id: 'run',
      chunks: [{ text: words ? `◐ ${d.running.length} running` : `◐ ${d.running.length}` }, { text: ' · ' }, { text: words ? `✓ ${d.done.length} done` : `✓ ${d.done.length}`, tone: 'dim' }],
    })
    if (d.prs && step < 4) {
      segments.push({ id: 'prs', chunks: [{ text: `${d.prs.open} ${d.prs.open === 1 ? 'PR' : 'PRs'}` }, ...(d.prs.failing > 0 ? [{ text: ` · ${d.prs.failing} ✗`, tone: 'error' as const }] : [])] })
    }
  }
  if (stale !== null) segments.push({ id: 'stale', chunks: [{ text: stale }] })
  else if (d.work && step < 2) segments.push(workSegment(d.work, step))
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

// ---- The details view: a header, one note line, and the columns.

export type Column = { key: 'needs' | 'running' | 'done' | 'prs'; label: string; count: string; line: string; tone?: Tone }
export type Details = {
  header: string[] // the first line sits beside the buttons; a second line holds what runs
  note: string | null // Loading, Stale or Partial, in one line under the header (F87)
  rows: Column[][] // four columns in a row; two rows of two below 60 columns
  colWidth: number
}

const JOIN = ' · '

// "goal 14m · 2 subagents · 1 background session": each part only above 0.
const runsText = (w: Work) =>
  [
    w.goalMs === null ? '' : `goal ${duration(w.goalMs)}`,
    w.subagents > 0 ? plural(w.subagents, 'subagent', 'subagents') : '',
    w.background > 0 ? plural(w.background, 'background session', 'background sessions') : '',
  ]
    .filter(Boolean)
    .join(JOIN)

// The header's cut ladder: 0 all, 1 no branch, 2 no session title, 3 "2/4 complete", 4 no milestone name (F84).
const headerAt = (w: Work, level: number) => {
  const m = w.milestone
  const branch = w.branch ?? (w.hasRepo ? DETACHED : null)
  const shown = m && w.branch?.includes(m.slug) ? null : branch // the slug is in the branch name: left out
  const parts = [w.repo]
  if (m) {
    if (level < 4) parts.push(m.slug)
    parts.push(level < 3 ? `${m.done} of ${m.total} features complete` : `${m.done}/${m.total} complete`)
  } else if (level < 2) parts.push(w.title ?? UNTITLED)
  if (level < 1 && shown !== null) parts.push(shown)
  return parts.join(JOIN)
}

const headerLines = (w: Work | null, columns: number): string[] => {
  if (w === null) return ['']
  const room = columns - BUTTONS_DETAILS
  const runs = runsText(w)
  const full = headerAt(w, 0)
  if (cells(full) <= room) return runs === '' ? [full] : cells(full + JOIN + runs) <= room ? [full + JOIN + runs] : [full, runs]
  let line = headerAt(w, 4)
  for (let level = 1; level <= 4; level++) {
    if (cells(headerAt(w, level)) <= room) {
      line = headerAt(w, level)
      break
    }
  }
  return runs === '' ? [line] : [line, runs] // what runs always has its own line once the header is cut
}

const column = (key: Column['key'], label: string, count: string, line: string, tone?: Tone): Column => ({ key, label, count, line, ...(tone ? { tone } : {}) })
const named = (l: Line) => `${l.repo}: ${l.title} ${duration(l.ms)}`

export const detailsLayout = (d: BandData, columns: number): Details => {
  const age = d.stale === null || d.stale.ageMs === null ? null : duration(d.stale.ageMs)
  const note = d.loading ? LOADING : d.stale ? staleWords(age, columns)[0]! : d.partial ? PRS_NOT_SHOWN : null
  const lines = columns >= 80 // below 80 the lines drop, except needs you
  const [need, run, fin] = [d.needs[0], d.running[0], d.done[0]]
  const prs = d.prs ? [column('prs', 'PRs', `${d.prs.open} open`, lines ? [d.prs.failing > 0 ? `${d.prs.failing} failing` : '', d.prs.mergeable > 0 ? `${d.prs.mergeable} mergeable` : ''].filter(Boolean).join(JOIN) : '', 'dim')] : []
  const cols: Column[] = d.loading
    ? []
    : [
        column('needs', 'needs you', String(d.needs.length), need ? (need.self ? `${THIS_SESSION} ${duration(need.ms)}` : named(need)) : ''),
        column('running', 'running', String(d.running.length), lines && run ? named(run) : '', 'dim'),
        column('done', 'done', String(d.done.length), lines && fin ? `${named(fin)} ago` : '', 'dim'),
        ...prs,
      ].map(c => (d.stale ? { ...c, tone: 'dim' as const } : c)) // a stale list dims the last counts
  const fold = columns < 60
  const rows = fold ? [cols.slice(0, 2), cols.slice(2)].filter(r => r.length > 0) : cols.length > 0 ? [cols] : []
  return { header: headerLines(d.work, columns), note, rows, colWidth: Math.max(10, Math.floor(columns / (fold ? 2 : 4)) - 2) }
}

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const fit = (s: string, max: number) => (s.length > max ? `${s.slice(0, Math.max(1, max - 1))}…` : s)
const FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
// The image cannot read the app's theme, so it follows the system's.
const STYLE = `.l,.s{fill:#87867f;font:12px ${FONT}}.v{fill:#1f1e1d;font:600 16px ${FONT}}.n{fill:#1f1e1d;font:12px ${FONT}}.d{stroke:#1f1e1d;stroke-opacity:.12}@media (prefers-color-scheme:dark){.v,.n{fill:#ecebe6}.d{stroke:#fff;stroke-opacity:.14}}`

// The columns as one image for the desktop: real dividers and exact columns (F37).
export const columnsSvg = (cols: Column[], width = 720): string => {
  const height = 64
  const colW = width / Math.max(1, cols.length)
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
