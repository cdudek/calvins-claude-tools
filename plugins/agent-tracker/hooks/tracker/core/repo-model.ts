// The Repo, Milestone and Feature pages, as the owner's drill-in mockup draws them (2026-11-14). Milestones, facts,
// questions and findings come from the change folders (core/change.ts); sessions, PRs and worktrees from the snapshot.
import type { Ask, Pr, SessionRecord, Snapshot } from '../types'
import { blockedReason, factVerdict, featureKind, featureSha, isFeatureComplete, isMerged, progressOf, stages, testsOf } from './change'
import type { Change, ChangeFeature } from './change'
import { cut, duration, pad, plural } from './format'
import { prsLine, repoPrs } from './git'
import { isLive, repoLabel } from './rank'
import { DOT, bar, dim, sp } from './paint'
import type { Span, Spans } from './paint'
import { GLYPH, clamp, firstKey, heading, hint, tidy, when } from './pane-model'
import type { Block, Item, Local, PaneModel, Page } from './pane-model'
import { HEADINGS, NO_PRS, PRS_NOT_SHOWN, UNTITLED } from './words'

export const ASKS_SHOWN = 6
export const WORKTREES_SHOWN = 8
export const PRS_SHOWN = 5
export const FACTS_ALL_MAX = 30 // more facts than this: the counts, and only the ones not met

const SECTION_SPAN = (text: string) => sp(text, undefined, { bold: true })

// ---- shared bits ----

// A PR's checks as the mockups draw them: ✓ green, ✗ red, ◌ yellow.
export const checksGlyph = (c: Pr['checks']): Span => (c === 'pass' ? sp('✓', 'green') : c === 'failing' ? sp('✗', 'red') : sp('◌', 'yellow'))


const oneLine = (text: string) => text.replace(/\s+/g, ' ').trim()

// The roots a repo's change folders can live in: the main checkout, then every worktree of its latest scan.
export const changeRoots = (snap: Snapshot, repoPath: string): { path: string; branch: string | null }[] => {
  const scans = snap.sessions.filter(r => r.repo?.path === repoPath && r.scan !== null).map(r => r.scan!)
  const latest = scans.reduce<(typeof scans)[number] | null>((best, s) => (best === null || s.at > best.at ? s : best), null)
  const trees = latest?.worktrees ?? []
  return [{ path: repoPath, branch: trees.find(w => w.path === repoPath)?.branch ?? null }, ...trees.filter(w => w.path !== repoPath)]
}

// One change per folder name: the copy in the worktree on its own branch is the live one, else the first found.
export const pickChanges = (found: Change[], roots: { path: string; branch: string | null }[]): Change[] => {
  const byDir = new Map<string, Change>()
  for (const c of found) {
    const have = byDir.get(c.dir)
    const mine = roots.find(r => r.path === c.root)?.branch === c.branch
    if (have === undefined || (mine && roots.find(r => r.path === have.root)?.branch !== have.branch)) byDir.set(c.dir, c)
  }
  return [...byDir.values()].sort((a, b) => b.dir.localeCompare(a.dir))
}

const prOn = (snap: Snapshot, repoPath: string, branch: string, now: number): Pr | undefined => {
  const p = repoPrs(snap.sessions, repoPath, now)
  return p !== null && p.ghOk ? p.prs.find(x => x.branch === branch) : undefined
}

// A session's glyph, by how much it needs you.
const glyphOf = (r: SessionRecord) => (isLive(r) ? GLYPH[r.state] : GLYPH.ended)

// ---- asks ----

const ASK_STATUS_SPAN = (a: Ask): Span => (a.status === 'needs-you' ? sp('● you', 'red') : a.status === 'in-progress' ? sp('◐', 'yellow') : sp('✓', 'green'))

// "13:40 T Fix login redirect   → fix-login-1   ◐": the time dim, T magenta, a question dimmed whole.
export const askLine = (a: Ask, r: SessionRecord, local: Local, columns: number, withMilestone: boolean): Spans => {
  const isQ = a.kind !== 'task'
  const arrow = withMilestone ? 16 : 0
  const tw = Math.max(8, columns - 6 - 2 - arrow - 6)
  const text = cut(oneLine(a.text), tw)
  const to = withMilestone ? (r.milestone ? dim(pad(cut(`→ ${r.milestone.slug}`, arrow - 1), arrow)) : sp(' '.repeat(arrow))) : sp('')
  return [dim(pad(when(a.at, local), 6)), a.kind === 'task' ? sp('T', 'magenta') : dim('Q'), sp(' '), isQ ? dim(pad(text, tw)) : sp(pad(text, tw)), sp(' '), to, ASK_STATUS_SPAN(a)]
}

const asksOf = (sessions: SessionRecord[]) => sessions.flatMap(r => r.asks.filter(a => a.kind !== 'not-classified').map(a => ({ a, r }))).sort((x, y) => y.a.at - x.a.at || x.r.sessionId.localeCompare(y.r.sessionId))

// ---- the Repo page ----

const milestoneRow = (c: Change, snap: Snapshot, repoPath: string, sessions: SessionRecord[], now: number, columns: number): Block => {
  const merged = isMerged(c)
  const needs = sessions.some(r => isLive(r) && r.state === 'needs-you' && r.milestone?.slug === c.slug) || c.features.some(f => featureKind(f.state) === 'blocked')
  const p = progressOf(c)
  const complete = p.total > 0 && p.done === p.total
  const glyph = merged ? sp('✓', 'dim') : needs ? sp('●', 'red') : complete ? sp('✓', 'green') : sp('◐', 'yellow')
  const pr = prOn(snap, repoPath, c.branch, now)
  const prSpans: Spans = pr ? [sp('#' + pr.number, 'cyan'), sp(' '), checksGlyph(pr.checks), ...(pr.behind === true ? [sp(' ↓', 'yellow')] : [])] : []
  const progress = `${p.done}/${p.total} ${p.unit === 'facts' ? 'facts' : 'features'}`
  const sw = clamp(columns - 2 - 1 - 13 - 1 - 6 - 1 - 7, 8, 18)
  const line: Spans = merged
    ? [glyph, sp(' '), dim(pad(cut(c.slug, sw), sw)), dim(' merged')]
    : [glyph, sp(' '), sp(pad(cut(c.slug, sw), sw)), sp(' '), sp(pad(progress, 13)), ...bar(p.done, p.total, 6), sp(' '), ...prSpans]
  const second: Spans[] = c.project !== null || c.ticket !== null ? [[sp('  '), dim(`project: ${[c.project, c.ticket].filter(Boolean).join(' · ')}`)]] : []
  return { kind: 'row', key: `milestone:${c.dir}`, to: { kind: 'milestone', repo: repoPath, change: c.dir }, lines: [line, ...second] }
}

// Worktrees with the state of the session in each, as one inline list.
const worktreeItems = (inRepo: SessionRecord[], snap: Snapshot, path: string, now: number): { items: Item[]; more: number } => {
  const scans = inRepo.flatMap(r => (r.scan ? [r.scan] : []))
  const latest = scans.reduce<(typeof scans)[number] | null>((best, s) => (best === null || s.at > best.at ? s : best), null)
  const trees = latest?.worktrees ?? []
  const treeOf = (cwd: string) => trees.filter(w => cwd === w.path || cwd.startsWith(`${w.path}/`)).sort((a, b) => b.path.length - a.path.length)[0]
  const rows = trees
    .map(w => {
      const mine = inRepo.filter(r => treeOf(r.cwd)?.path === w.path).sort((a, b) => b.lastActivityAt - a.lastActivityAt)
      const live = mine.filter(isLive)
      const top = live.find(r => r.state === 'needs-you') ?? live.find(r => r.state === 'running') ?? live[0] ?? mine[0]
      const label = w.path === path ? 'main checkout' : w.path.startsWith(`${path}/`) ? w.path.slice(path.length + 1).replace(/^\.worktrees\//, '') : (w.path.split('/').pop() ?? w.path)
      const at = Math.max(0, ...mine.map(r => Math.max(r.lastActivityAt, r.endedAt ?? 0)))
      return { w, top, label, live: live.length > 0, at, mine }
    })
    .sort((a, b) => Number(b.live) - Number(a.live) || b.at - a.at || a.w.path.localeCompare(b.w.path))
  const shown = rows.slice(0, WORKTREES_SHOWN)
  const state = (x: (typeof rows)[number]): Spans =>
    x.top === undefined ? [dim(' ○')] : isLive(x.top) ? [sp(' '), GLYPH[x.top.state]] : [dim(` ○ ${duration(now - x.at)}`)]
  const items: Item[] = shown.map(x => ({ key: `worktree:${x.w.path}`, spans: [sp(cut(x.label, 20)), ...state(x)], ...(x.top ? { to: { kind: 'session', id: x.top.sessionId } as Page } : {}) }))
  return { items, more: rows.length - shown.length }
}

export const repoModel = (snap: Snapshot, path: string, changes: Change[], now: number, local: Local, columns: number): PaneModel | null => {
  const inRepo = snap.sessions.filter(r => r.repo?.path === path)
  if (inRepo.length === 0) return null
  const label = repoLabel(inRepo[0]!)
  const needs = inRepo.filter(r => isLive(r) && r.state === 'needs-you').length
  const blocks: Block[] = [{ kind: 'rule' }]

  if (changes.length > 0) {
    const open = [...changes].sort((a, b) => Number(isMerged(a)) - Number(isMerged(b)) || b.dir.localeCompare(a.dir))
    blocks.push({ kind: 'lines', key: 'milestones-head', lines: [heading(HEADINGS.milestones)] }, ...open.map(c => milestoneRow(c, snap, path, inRepo, now, columns)), { kind: 'rule' })
  }

  const asks = asksOf(inRepo)
  const tasks = asks.filter(x => x.a.kind === 'task').length
  const questions = asks.length - tasks
  const openAsks = asks.filter(x => x.a.status !== 'replied').length
  const withMilestone = asks.some(x => x.r.milestone !== null)
  blocks.push({ kind: 'lines', key: 'asks-head', lines: [heading(HEADINGS.asks, undefined, [sp('  '), dim(`${plural(tasks, 'task', 'tasks')} · ${plural(questions, 'question', 'questions')} · ${openAsks} open`)])] })
  blocks.push(...asks.slice(0, ASKS_SHOWN).map(({ a, r }): Block => ({ kind: 'row', key: `ask:${r.sessionId}:${a.n}`, to: { kind: 'session', id: r.sessionId }, lines: [askLine(a, r, local, columns, withMilestone)] })))
  if (asks.length === 0) blocks.push({ kind: 'lines', key: 'asks-none', lines: [[dim('No asks yet.')]] })
  else if (asks.length > ASKS_SHOWN) blocks.push({ kind: 'lines', key: 'asks-more', lines: [[dim(`and ${asks.length - ASKS_SHOWN} more`)]] })
  blocks.push({ kind: 'rule' })

  const trees = worktreeItems(inRepo, snap, path, now)
  if (trees.items.length > 0) blocks.push({ kind: 'inline', key: 'worktrees', head: [SECTION_SPAN(HEADINGS.worktrees), sp('  ')], items: [...trees.items, ...(trees.more > 0 ? [{ key: 'worktrees:more', spans: [dim(`+${trees.more}`)] }] : [])], sep: DOT })

  // OTHER PRs: the open PRs no milestone of this repo carries.
  const found = repoPrs(snap.sessions, path, now)
  const taken = new Set(changes.map(c => c.branch))
  if (found !== null && found.github) {
    if (!found.ghOk) blocks.push({ kind: 'lines', key: 'prs-note', wrap: true, lines: [[SECTION_SPAN(HEADINGS.otherPrs), sp('  '), dim(PRS_NOT_SHOWN)]] })
    else {
      const rest = [...found.prs].filter(p => !taken.has(p.branch)).sort((a, b) => Number(b.checks === 'failing') - Number(a.checks === 'failing') || b.createdAt.localeCompare(a.createdAt) || b.number - a.number)
      const items: Item[] = rest.slice(0, PRS_SHOWN).flatMap((p): Item[] => [
        { key: `pr:${p.number}`, href: p.url, spans: [sp(`#${p.number}`, 'cyan')] },
        { key: `pr:${p.number}:title`, spans: [sp(` ${cut(oneLine(p.title), 14)} `), checksGlyph(p.checks)] },
      ])
      const line = rest.length === 0 ? [dim(NO_PRS)] : []
      blocks.push({ kind: 'inline', key: 'other-prs', head: [SECTION_SPAN(HEADINGS.otherPrs), sp('  '), ...line], items: [...items, ...(rest.length > PRS_SHOWN ? [{ key: 'prs:more', spans: [dim(`+${rest.length - PRS_SHOWN}`)] }] : [])], sep: DOT })
      const stored = prsLine(found)
      if (stored !== null) blocks.push({ kind: 'lines', key: 'prs-stored', lines: [[dim(stored)]] })
    }
  }

  return {
    crumbs: [{ text: 'Home', to: { kind: 'home' } }, { text: label, to: null, bold: true }],
    right: needs > 0 ? [sp(`${needs} ${needs === 1 ? 'needs' : 'need'} you`, 'red')] : [],
    blocks: tidy(blocks),
    footer: hint(),
    first: firstKey(blocks),
  }
}

// ---- the Milestone page ----

const FACT_TONE = { met: 'green', unmet: 'red', open: 'dim' } as const

const factSpans = (c: Change, ids: string[]): Spans => ids.flatMap((id, i) => [...(i > 0 ? [sp(' ')] : []), sp(id, FACT_TONE[factVerdict(c, id)])])

const stageSpans = (c: Change): Spans =>
  stages(c).flatMap((s): Spans => {
    const mark = s.state === 'done' ? sp('✓', 'green') : s.state === 'active' ? sp('◐', 'yellow') : sp('○', 'dim')
    const name = s.name === null ? [] : [s.state === 'todo' ? dim(` ${s.name}`) : s.state === 'active' ? sp(` ${s.name}`, 'yellow') : sp(` ${s.name}`)]
    return [...(s.n > 1 ? [sp('  ')] : []), s.state === 'todo' ? dim(String(s.n)) : sp(String(s.n)), sp(' '), ...(s.name === null ? [mark] : [...name, sp(' '), mark])]
  })

const featureRow = (c: Change, f: ChangeFeature, repoPath: string, columns: number): Block => {
  const kind = featureKind(f.state)
  const glyph = kind === 'done' || kind === 'merged' ? sp('✓', 'green') : kind === 'building' ? sp('◐', 'yellow') : kind === 'blocked' ? sp('✗', 'red') : sp('○', 'dim')
  const right: Span = kind === 'done' ? dim(featureSha(f) ?? '') : kind === 'merged' ? dim('merged') : kind === 'building' ? sp('building', 'yellow') : kind === 'blocked' ? sp(cut(`blocked: ${blockedReason(f)}`, 34), 'red') : sp('')
  const room = Math.max(8, columns - 2 - 3 - right.text.length - 1)
  const name = `${f.n} ${cut(f.name, room - 2)}`
  const line: Spans = [glyph, sp(' '), kind === 'todo' ? dim(pad(name, room)) : sp(pad(name, room)), sp(' '), right]
  return { kind: 'row', key: `feature:${f.n}`, to: { kind: 'feature', repo: repoPath, change: c.dir, n: f.n }, lines: [line] }
}

export const milestoneNotFound = (text: string) => `No milestone "${text}" in this repo. Pick one on the Repo page.`

export const milestoneModel = (snap: Snapshot, repoPath: string, c: Change, now: number, columns: number): PaneModel | null => {
  const inRepo = snap.sessions.filter(r => r.repo?.path === repoPath)
  const repoName = inRepo[0] ? repoLabel(inRepo[0]) : (repoPath.split('/').pop() ?? repoPath)
  const pr = prOn(snap, repoPath, c.branch, now)
  const done = c.features.filter(isFeatureComplete).length
  const blocks: Block[] = [
    { kind: 'lines', key: 'where', lines: [[dim(`changes/${c.dir} · branch ${c.branch}`)]] },
    {
      kind: 'inline',
      key: 'ticket-pr',
      head: [...(c.ticket !== null ? [dim('ticket '), sp(c.ticket, 'cyan'), sp('   ')] : []), dim('PR ')],
      items: pr ? [{ key: 'pr', href: pr.url, spans: [sp(`#${pr.number}`, 'cyan')] }, { key: 'pr:checks', joined: true, spans: [sp(' '), checksGlyph(pr.checks)] } as Item] : [{ key: 'pr:none', spans: [dim('not yet (gate first)')] }],
      sep: null,
    },
    { kind: 'rule' },
    { kind: 'lines', key: 'stage', wrap: true, lines: [[SECTION_SPAN(HEADINGS.stage), sp('  '), ...stageSpans(c)]] },
    { kind: 'lines', key: 'features-head', lines: [[SECTION_SPAN(HEADINGS.features), sp(pad('', Math.max(1, columns - 2 - HEADINGS.features.length - `${done}/${c.features.length}`.length))), dim(`${done}/${c.features.length}`)]] },
    ...c.features.map(f => featureRow(c, f, repoPath, columns)),
  ]
  // FACTS: the ids coloured by the last gate report; with many, the counts and only the ones not met.
  if (c.facts.length > 0) {
    const ids = c.facts.map(f => f.id)
    const met = ids.filter(id => factVerdict(c, id) === 'met').length
    const listed = ids.length <= FACTS_ALL_MAX ? ids : ids.filter(id => factVerdict(c, id) !== 'met')
    const counts = ids.length <= FACTS_ALL_MAX ? [] : [sp(`${met}/${ids.length} met`, 'green'), ...(listed.length > 0 ? [sp(' · '), dim('not met: ')] : [])]
    blocks.push({ kind: 'lines', key: 'facts', wrap: true, lines: [[SECTION_SPAN(HEADINGS.facts), sp('  '), ...counts, ...factSpans(c, listed)]] })
  }
  if (c.questions.length > 0) {
    const q = c.questions[c.questions.length - 1]!
    blocks.push({ kind: 'lines', key: 'questions', wrap: true, lines: [[SECTION_SPAN(HEADINGS.questions), sp('  '), sp(`${c.questions.length} open`, 'red'), sp('  '), dim(`"${cut(q.title, 60)}"`), ...(q.fallback !== '' ? [dim(` default: ${cut(q.fallback, 50)}`)] : [])]] })
  }
  blocks.push({
    kind: 'lines',
    key: 'findings',
    lines: [[SECTION_SPAN(HEADINGS.findings), sp('   '), ...(c.findings === null ? [dim('none yet (review runs at close)')] : [c.findings.open > 0 ? sp(`${c.findings.open} open`, 'red') : dim('none open'), ...(c.findings.fixed > 0 ? [DOT, sp(`${c.findings.fixed} fixed`, 'green')] : [])])]],
  })
  const here = inRepo.filter(r => r.milestone?.slug === c.slug).sort((a, b) => Number(isLive(b)) - Number(isLive(a)) || b.lastActivityAt - a.lastActivityAt)
  if (here.length > 0) {
    const items: Item[] = here.slice(0, 6).map(r => ({ key: `session:${r.sessionId}`, to: { kind: 'session', id: r.sessionId }, spans: [glyphOf(r), sp(' '), isLive(r) ? sp(cut(r.title ?? UNTITLED, 22)) : dim(cut(r.title ?? UNTITLED, 22))] }))
    blocks.push({ kind: 'inline', key: 'sessions', head: [SECTION_SPAN(HEADINGS.sessions), sp('   ')], items: [...items, ...(here.length > 6 ? [{ key: 'sessions:more', spans: [dim(`+${here.length - 6}`)] }] : [])], sep: DOT })
  }
  return {
    crumbs: [{ text: 'Home', to: { kind: 'home' } }, { text: repoName, to: { kind: 'repo', path: repoPath } }, ...(c.project !== null ? [{ text: c.project, to: null }] : []), { text: c.slug, to: null, bold: true }],
    right: [],
    blocks: tidy([{ kind: 'rule' }, ...blocks]),
    footer: hint(),
    first: firstKey(blocks),
  }
}

// ---- the Feature page ----

const FEATURE_STATE = (f: ChangeFeature): Spans => {
  const kind = featureKind(f.state)
  return kind === 'done' ? [sp('✓ done', 'green'), ...(featureSha(f) ? [dim(` ${featureSha(f)}`)] : [])] : kind === 'merged' ? [sp('✓ merged', 'green')] : kind === 'building' ? [sp('◐ building', 'yellow')] : kind === 'blocked' ? [sp('✗ blocked', 'red')] : [dim('○ to do')]
}

export const featureModel = (snap: Snapshot, repoPath: string, c: Change, n: number, now: number, columns: number): PaneModel | null => {
  const f = c.features.find(x => x.n === n)
  if (f === undefined) return null
  const ids = c.facts.filter(x => x.feature === n).map(x => x.id)
  const tests = testsOf(c, n)
  const blocks: Block[] = [{ kind: 'lines', key: 'name', wrap: true, lines: [[sp(f.name)]] }]
  if (ids.length > 0) blocks.push({ kind: 'lines', key: 'facts', wrap: true, lines: [[dim('facts '), ...factSpans(c, ids)]] })
  if (featureKind(f.state) === 'blocked') blocks.push({ kind: 'lines', key: 'blocked', wrap: true, lines: [[sp(`blocked: ${blockedReason(f)}`, 'red')]] })
  blocks.push({ kind: 'rule' })
  if (tests.length > 0)
    blocks.push({ kind: 'lines', key: 'tests', lines: [[SECTION_SPAN(HEADINGS.tests)], ...tests.map(t => [sp(` ${cut(t.file, Math.max(10, columns - 24))}  `), t.met === t.total ? sp(`${t.met} met`, 'green') : sp(`${t.total - t.met} not met`, 'red')])] })
  // BUILDER: the session on this milestone that works now, for the feature being built.
  const builder = featureKind(f.state) === 'building' ? snap.sessions.filter(r => r.repo?.path === repoPath && r.milestone?.slug === c.slug && isLive(r) && r.state !== 'done').sort((a, b) => b.lastActivityAt - a.lastActivityAt)[0] : undefined
  if (builder !== undefined) {
    const tok = (x: number) => (x < 1000 ? String(x) : x < 1_000_000 ? `${Math.round(x / 1000)}k` : `${(x / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`)
    const u = builder.usage
    blocks.push({
      kind: 'lines',
      key: 'builder',
      lines: [
        [SECTION_SPAN(HEADINGS.builder), sp('  '), sp(cut(builder.title ?? UNTITLED, 30)), DOT, dim(`${duration(now - builder.startedAt)}`)],
        [sp(' '), dim('tokens '), sp(`${tok(u.tokensIn)} in`), DOT, sp(`${tok(u.tokensOut)} out`)],
        [sp(' '), dim('struggles '), u.retries > 0 ? sp(plural(u.retries, 'retry', 'retries'), 'yellow') : dim('0 retries'), DOT, u.toolErrors > 0 ? sp(plural(u.toolErrors, 'tool error', 'tool errors'), 'yellow') : dim('0 tool errors')],
      ],
    })
    blocks.push({ kind: 'row', key: `session:${builder.sessionId}`, to: { kind: 'session', id: builder.sessionId }, lines: [[dim(' open the session')]] })
  }
  return {
    crumbs: [{ text: '…', to: { kind: 'repo', path: repoPath } }, { text: c.slug, to: { kind: 'milestone', repo: repoPath, change: c.dir } }, { text: cut(`${n} ${f.name.replace(/`/g, '')}`, Math.max(12, columns - c.slug.length - 20)), to: null, bold: true }],
    right: FEATURE_STATE(f),
    blocks: tidy([{ kind: 'rule' }, ...blocks]),
    footer: hint(),
    first: firstKey(blocks),
  }
}
