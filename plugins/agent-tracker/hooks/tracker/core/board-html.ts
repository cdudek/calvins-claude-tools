// The web page as plain data in, one HTML string out: no engine, file, process or clock access. The page draws itself
// in the browser from an inline JSON block with textContent, so no value is ever put into markup. The only text that
// reaches the HTML is that block, with `<`, `>` and `&` written as \u escapes, and the count in the title.
import type { SessionRecord, Snapshot } from '../types'
import { clean, resumeCommand } from './format'
import { repoPrs } from './git'
import { isLive, repoLabel } from './rank'
import { mergedKey, taskCounts, taskItems } from './tasks'
import { turnKey } from './notes'
import { ASK_KIND, ASK_STATUS, CHECKS_WORDS, DETACHED, MERGE_WORDS, REASON_WORDS, REVIEW_WORDS, UNTITLED } from './words'

export const BOARD_FILE = 'board.html'
export const BOARD_PATH_TEXT = '~/.claude/agent-tracker/board.html'
export const BOARD_RELOAD_MS = 5000
export const BOARD_STALE_MS = 3 * 60_000 // no session rewrote the page for this long: one amber line under the top bar
export const BOARD_WRITE_MS = 10_000

// "You should know" and "Decided without you": a field another part of the mod adds to a session record. Read when
// present, shown as nothing when absent.
export type Note = { id: string; kind: 'know' | 'decided'; text: string; at: number; seen: boolean }

// The files of one change folder the pages read; each is the file's text, absent when the folder has no such file.
export type ChangeFiles = { repoPath: string; folder: string; milestone: string; facts?: string; validation?: string; questions?: string; findings?: string; done?: string }

const SESSIONS_MAX = 300
const ASKS_KEPT = 30
const DAYS = 7 * 24 * 3600 * 1000
const TEXT = 300

type Row = Record<string, unknown>
const cells = (line: string) => line.split('|').map(c => c.trim())

// What the owner marked in settings.json (the Board only reads it): notes seen, tasks kept and closed.
export type Marks = { seen: ReadonlySet<string>; kept: ReadonlySet<string>; closed: ReadonlySet<string> }
const noMarks: Marks = { seen: new Set(), kept: new Set(), closed: new Set() }

export const notesOf = (r: SessionRecord, seen: ReadonlySet<string> = noMarks.seen): Note[] => {
  const list = (r as { notes?: unknown }).notes
  if (!Array.isArray(list)) return []
  return (list as Row[])
    .filter(n => n !== null && typeof n === 'object' && (n.kind === 'know' || n.kind === 'decided') && typeof n.at === 'number')
    .map((n, i) => {
      const id = clean(n.id ?? i, 80)
      return { id, kind: n.kind as Note['kind'], text: clean(n.text, TEXT), at: n.at as number, seen: n.seen === true || seen.has(turnKey(r.sessionId, id)) }
    })
}

// milestone.md, the Features table with its PR or commit cell (parseMilestone keeps no cell but name and state).
const featureRows = (text: string) =>
  text
    .split('\n')
    .map(cells)
    .filter(c => c.length >= 6 && /^\d+$/.test(c[1]!))
    .map(c => ({ n: Number(c[1]), name: clean(c[3], TEXT), ref: clean(c[4], 80), state: clean(c[5], TEXT) }))

const front = (text: string, key: string) => new RegExp(`^${key}:\\s*(.+?)\\s*$`, 'm').exec(/^---\n([\s\S]*?)\n---/.exec(text)?.[1] ?? '')?.[1]

type Fact = { id: string; feature: number | null; text: string | null; verdict: string | null; check: string | null }

// facts.md gives each fact's words, done.json its feature and check, validation.md its verdict (the last cell of its row).
const factsOf = (c: ChangeFiles): Fact[] => {
  const words = new Map<string, string>()
  for (const m of (c.facts ?? '').matchAll(/^- \[[ x]\] \*\*(F\d+)\*\*\s*(?:\([^)]*\))?\s*(.+)$/gm)) words.set(m[1]!, clean(m[2], TEXT))
  const verdicts = new Map<string, string>()
  for (const line of (c.validation ?? '').split('\n')) {
    const cs = cells(line)
    if (cs.length >= 4 && /^F\d+$/.test(cs[1]!)) verdicts.set(cs[1]!, clean(cs[cs.length - 2], 60))
  }
  let listed: { id: string; feature: number | null; check: string | null }[] = []
  try {
    const parsed = JSON.parse(c.done ?? '{}') as { facts?: Row[] }
    listed = (parsed.facts ?? []).filter(f => typeof f?.id === 'string').map(f => ({ id: String(f.id), feature: typeof f.feature === 'number' ? f.feature : null, check: typeof f.check === 'string' ? clean(f.check, TEXT) : null }))
  } catch {
    // a torn or missing done.json: the facts come from facts.md alone
  }
  const ids = listed.length > 0 ? listed : [...words.keys()].map(id => ({ id, feature: null, check: null }))
  return ids.map(f => ({ ...f, text: words.get(f.id) ?? null, verdict: verdicts.get(f.id) ?? null }))
}

// questions.md: `- **Q7 (F4, step 3): the question?** ... **Default taken:** ... **To change:** ...`
const questionsOf = (text: string | undefined) =>
  [...(text ?? '').matchAll(/^- \*\*(Q\d+)\b([^*]*)\*\*\s*(.*)$/gm)].map(m => ({
    id: m[1]!,
    text: clean(m[2]!.replace(/^[\s:]+/, '').replace(/^\([^)]*\):?\s*/, ''), TEXT),
    taken: clean(/\*\*Default taken:\*\*\s*(.*?)(?:\s*\*\*To change:\*\*|$)/.exec(m[3]!)?.[1], TEXT),
  }))

// findings.md: `- [ ] **S1 title** ...` open, `- [x]` fixed; items under "## Advisory" do not block.
const findingsOf = (text: string | undefined) => {
  let advisory = false
  const items: { open: boolean; text: string }[] = []
  for (const line of (text ?? '').split('\n')) {
    if (line.startsWith('## ')) advisory = /^##\s+Advisory/i.test(line)
    const m = /^- \[([ x])\]\s*(.+)$/.exec(line)
    if (m !== null && !advisory) items.push({ open: m[1] === ' ', text: clean(m[2]!.replace(/\*\*/g, ''), TEXT) })
  }
  return items
}

const milestoneOf = (c: ChangeFiles) => {
  const slug = clean(front(c.milestone, 'milestone'), 200)
  const branch = clean(front(c.milestone, 'branch'), 200)
  if (slug === '' || branch === '') return null
  return {
    repoPath: c.repoPath,
    slug,
    branch,
    change: clean(c.folder, 200),
    sentence: clean(/^>\s*(.+)$/m.exec(c.milestone)?.[1], TEXT),
    features: featureRows(c.milestone),
    facts: factsOf(c),
    questions: questionsOf(c.questions),
    findings: findingsOf(c.findings),
  }
}

const sessionOf = (r: SessionRecord, snap: Snapshot, now: number, seen: ReadonlySet<string>) => {
  const prs = r.repo ? repoPrs(snap.sessions, r.repo.path, now) : null
  const onBranch = prs !== null && prs.ghOk && r.branch !== null ? prs.prs.find(p => p.branch === r.branch) : undefined
  return {
    id: r.sessionId,
    repo: repoLabel(r),
    repoPath: r.repo?.path ?? null,
    title: r.title ?? UNTITLED,
    state: r.state,
    reason: r.reason,
    unknownValue: r.unknownValue,
    live: isLive(r),
    branch: r.branch ?? (r.repo ? DETACHED : null),
    since: r.engine.since,
    startedAt: r.startedAt,
    lastActivityAt: r.lastActivityAt,
    endedAt: r.state === 'ended' ? (r.endedAt ?? r.lastActivityAt) : r.endedAt, // an ended session with no end time ended at its last activity
    source: r.source,
    usage: { in: r.usage.tokensIn, out: r.usage.tokensOut, errors: r.usage.toolErrors, retries: r.usage.retries },
    goalSince: r.runs.goalSince,
    subagents: r.runs.subagents.map(a => ({ name: a.name, status: a.status })),
    background: r.runs.background.map(b => ({ name: b.name, since: b.since })),
    asks: r.asks.slice(-ASKS_KEPT).map(a => ({ n: a.n, kind: a.kind, status: a.status, at: a.at, text: clean(a.text, TEXT) })),
    asksTotal: r.asks.length,
    milestone: r.milestone,
    pr: onBranch ? { number: onBranch.number, url: onBranch.url, checks: onBranch.checks } : null,
    notes: notesOf(r, seen),
    resume: r.state === 'ended' ? resumeCommand(r.cwd, r.sessionId) : null,
  }
}

export type BoardData = ReturnType<typeof boardData>

// Everything the pages need. A session older than a week with nothing live about it is left out, so the page stays small.
export const boardData = (snap: Snapshot, changes: ChangeFiles[], now: number, marks: Marks = noMarks) => {
  const recent = snap.sessions
    .filter(r => isLive(r) || Math.max(r.lastActivityAt, r.endedAt ?? 0) >= now - DAYS)
    .sort((a, b) => Math.max(b.lastActivityAt, b.endedAt ?? 0) - Math.max(a.lastActivityAt, a.endedAt ?? 0))
    .slice(0, SESSIONS_MAX)
  const paths = [...new Set(recent.flatMap(r => (r.repo ? [r.repo.path] : [])))]
  const repos = paths.map(path => {
    const prs = repoPrs(snap.sessions, path, now)
    const scans = snap.sessions.filter(r => r.repo?.path === path && r.scan !== null).map(r => r.scan!)
    const trees = scans.reduce<(typeof scans)[number] | null>((best, s) => (best === null || s.at > best.at ? s : best), null)?.worktrees ?? []
    return {
      path,
      label: repoLabel(recent.find(r => r.repo?.path === path)!),
      prs: prs && { at: prs.at, ghOk: prs.ghOk, github: prs.github, hasLive: prs.hasLive, list: prs.prs },
      worktrees: trees,
    }
  })
  // A change whose milestone.md says merged finishes the tasks of the session on its branch.
  const merged = new Set(changes.flatMap(c => (/^(merged|released|shipped)\b/i.test(front(c.milestone, 'status') ?? '') ? [mergedKey(c.repoPath, clean(front(c.milestone, 'branch'), 200))] : [])))
  const tasks = taskItems(snap, now, { kept: marks.kept, closed: marks.closed, merged })
  return {
    v: 1 as const,
    builtAt: now,
    agentsOk: snap.agentsOk,
    stale: snap.at !== 0 && snap.failedReads >= 2,
    loading: snap.at === 0,
    sessions: recent.map(r => sessionOf(r, snap, now, marks.seen)),
    tasks,
    counts: taskCounts(tasks),
    repos,
    milestones: changes.flatMap(c => {
      const m = paths.includes(c.repoPath) ? milestoneOf(c) : null
      return m === null ? [] : [m]
    }),
    words: { reason: REASON_WORDS, askKind: ASK_KIND, askStatus: ASK_STATUS, checks: CHECKS_WORDS, review: REVIEW_WORDS, merge: MERGE_WORDS },
  }
}

// The count in the tab title: sessions that need you now.
export const needsCount = (d: BoardData) => d.sessions.filter(s => s.live && s.state === 'needs-you').length
export const titleOf = (n: number) => (n > 0 ? `(${n}) Agent tracker - your tasks not done yet` : 'Agent tracker - your tasks not done yet')

// A JSON block inside a <script>: nothing in it can close the tag or start a comment.
export const inlineJson = (value: unknown) =>
  JSON.stringify(value).replace(/[<>&\u2028\u2029]/g, c => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`)
